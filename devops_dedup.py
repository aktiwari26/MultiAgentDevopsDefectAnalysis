"""Incident de-duplication: one Jira ticket and one alert per distinct incident
inside a time window.

An incident's fingerprint is a hash of its normalised failure evidence (the
error lines of the raw log with timestamps, ids and numbers removed), so
re-running the same log, or a later recurrence with different timestamps and
request ids, maps to the same key. State lives in a small JSON file so it
survives restarts; writes are atomic and guarded by a lock.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from config import Config
from devops_rag import _signature_lines

_lock = threading.Lock()

_TIMESTAMP = re.compile(
    r"\b\d{4}[-/]\d{2}[-/]\d{2}(?:[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?)?\b|\b\d{1,2}:\d{2}:\d{2}(?:[.,]\d+)?\b"
)
_IDENTIFIER = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b|\b0x[0-9a-f]+\b|\b[0-9a-f]{16,}\b",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"\d+")
_SPACE = re.compile(r"\s+")


def _normalise(line: str) -> str:
    line = _TIMESTAMP.sub(" ", line.lower())
    line = _IDENTIFIER.sub(" ", line)
    line = _NUMBER.sub("#", line)
    return _SPACE.sub(" ", line).strip()


def fingerprint(raw_logs: str) -> str:
    """Stable 16-hex-digit fingerprint of an incident's failure evidence."""
    lines = _signature_lines(raw_logs or "", limit=40, width=300)
    normalised = sorted({n for n in (_normalise(line) for line in lines) if n})
    digest = hashlib.sha256("\n".join(normalised).encode("utf-8")).hexdigest()
    return digest[:16]


def _store_path(path: Optional[str]) -> Path:
    return Path(path or Config.DEDUP_STORE_PATH)


def _read(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".dedup_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _fresh(entry: dict, ttl_hours: float, now: float) -> bool:
    return now - float(entry.get("updated_at", 0)) <= ttl_hours * 3600


def get(fp: str, path: Optional[str] = None, ttl_hours: Optional[float] = None) -> Optional[dict]:
    """The stored record for `fp` if it is still inside the TTL, else None."""
    ttl = Config.DEDUP_TTL_HOURS if ttl_hours is None else ttl_hours
    with _lock:
        entry = _read(_store_path(path)).get(fp)
    return entry if entry and _fresh(entry, ttl, time.time()) else None


def update(
    fp: str,
    path: Optional[str] = None,
    ttl_hours: Optional[float] = None,
    ticket: Optional[dict] = None,
    notified: bool = False,
) -> dict:
    """Record a ticket and/or that an alert went out for `fp`; prunes expired
    entries. Returns the stored record."""
    ttl = Config.DEDUP_TTL_HOURS if ttl_hours is None else ttl_hours
    target = _store_path(path)
    now = time.time()
    with _lock:
        data = {k: v for k, v in _read(target).items() if _fresh(v, ttl, now)}
        entry = data.get(fp) or {"first_seen": now, "count": 0}
        entry["count"] = int(entry.get("count", 0)) + 1
        entry["updated_at"] = now
        if ticket is not None:
            entry["ticket"] = ticket
        if notified:
            entry["notified_at"] = now
        data[fp] = entry
        _write(target, data)
    return entry
