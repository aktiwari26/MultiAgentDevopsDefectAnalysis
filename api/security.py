"""Request protection for the FastAPI app: optional bearer-token auth, a small
in-process rate limiter, and an allowlist for client-supplied LLM base URLs.

Everything reads `Config` at call time so behaviour follows the environment
(and tests can change it) without re-importing.
"""
from __future__ import annotations

import hmac
import ipaddress
import threading
import time
from collections import defaultdict, deque
from typing import Callable
from urllib.parse import urlparse

from fastapi import HTTPException, Request

from config import Config

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _presented_token(headers, query_token: str | None = None) -> str:
    auth = headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return headers.get("x-api-key", "").strip() or (query_token or "").strip()


def token_ok(presented: str) -> bool:
    expected = Config.API_AUTH_TOKEN
    return bool(expected) and hmac.compare_digest(presented.encode(), expected.encode())


def require_auth(request: Request) -> None:
    """FastAPI dependency. A no-op while API_AUTH_TOKEN is unset (local
    development); otherwise the request must carry the token."""
    if not Config.API_AUTH_TOKEN:
        return
    if not token_ok(_presented_token(request.headers)):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid API token",
            headers={"WWW-Authenticate": "Bearer"},
        )


class SlidingWindowLimiter:
    """Per-key sliding-window counter (in-process; one instance per worker)."""

    def __init__(self, window_s: float = 60.0):
        self.window_s = window_s
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, now: float | None = None) -> tuple[bool, float]:
        """Returns (allowed, retry_after_seconds)."""
        if limit <= 0:
            return True, 0.0
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self.window_s:
                hits.popleft()
            if len(hits) >= limit:
                return False, max(0.0, self.window_s - (now - hits[0]))
            hits.append(now)
            return True, 0.0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def rate_limit(bucket: str, limit_attr: str) -> Callable[[Request], None]:
    """Dependency factory: limit `bucket` per client IP to Config.<limit_attr>
    requests per minute (0 disables)."""

    def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        allowed, retry_after = limiter.allow(f"{bucket}:{client}", getattr(Config, limit_attr))
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

    return dependency


def allowed_base_url_hosts() -> set[str]:
    hosts = set(_LOCAL_HOSTS) | set(Config.ALLOWED_BASE_URL_HOSTS)
    configured = urlparse(Config.OPENROUTER_BASE_URL).hostname
    if configured:
        hosts.add(configured.lower())
    return hosts


def validate_base_url(url: str) -> str:
    """Reject client-supplied LLM base URLs that are not http(s) to an
    allowlisted host, so the server cannot be used to forward prompts (which
    contain logs) to an arbitrary destination."""
    parsed = urlparse(url.strip())
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or not host:
        raise HTTPException(status_code=400, detail="base_url must be an http(s) URL")
    if host in allowed_base_url_hosts():
        return url.strip()
    try:
        ipaddress.ip_address(host)
        detail = "base_url host is not allowed"
    except ValueError:
        detail = f"base_url host '{host}' is not on the allowlist (set ALLOWED_BASE_URL_HOSTS to permit it)"
    raise HTTPException(status_code=400, detail=detail)
