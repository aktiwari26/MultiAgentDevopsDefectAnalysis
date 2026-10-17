"""FastAPI backend for the DevOps Incident Analysis Suite's React dashboard.

Serves the SSE-streamed 7-agent pipeline (devops_graph.build_graph()) at
POST /analyze, the human-approval step at POST /approve/{request_id}, connection
health at GET /health, bundled sample logs at GET /samples/{name}, a live log
relay at WS /ws/logs (fed by POST /webhook/logs), and — once built — the React
dashboard itself as static files, all from this single process/port.
Run from the project root: `uvicorn api.main:app --port 8000`.

Protection (see api/security.py and devops_security.py): optional bearer-token
auth (API_AUTH_TOKEN), per-IP rate limits, a payload size cap, secret/PII
redaction and prompt-injection tagging of submitted logs, and an allowlist for
client-supplied LLM base URLs.
"""
import json
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from config import Config
from devops_state import apply_update, base_state
from devops_graph import approval_router, build_graph
from devops_agents import jira_node, notification_node
from devops_security import neutralize_injection, redact
from api.security import (
    _presented_token,
    rate_limit,
    require_auth,
    token_ok,
    validate_base_url,
)

app = FastAPI(title="DevOps API", version="1.1.0")

SAMPLES_DIR = Path(__file__).parent.parent / "data" / "sample_logs"


class ConnectionManager:
    """Tracks open /ws/logs WebSocket connections so /webhook/logs can
    broadcast incoming log lines to every connected dashboard tab."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                continue


manager = ConnectionManager()


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    if Config.API_AUTH_TOKEN:
        presented = _presented_token(websocket.headers, websocket.query_params.get("token"))
        if not token_ok(presented):
            await websocket.close(code=1008)
            return
    await manager.connect(websocket)
    try:
        while True:
            # The dashboard's Live Stream tab only receives; it never sends,
            # but we still need to await something to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post(
    "/webhook/logs",
    dependencies=[Depends(require_auth), Depends(rate_limit("webhook", "WEBHOOK_RATE_LIMIT_PER_MIN"))],
)
async def webhook_logs(request: Request):
    """Push one log line to every connected /ws/logs client (a relay only: the
    line is displayed, not analysed). Accepts {"log": "<line>"} (or any JSON
    body — falls back to its str()), or a raw text body if the request isn't
    valid JSON at all. Lines are size-capped and, unless REDACT_LOGS is off,
    redacted before being broadcast."""
    body = await request.body()
    if len(body) > 64_000:
        raise HTTPException(status_code=413, detail="Webhook payload too large")
    try:
        data = json.loads(body)
        log_entry = data.get("log", str(data)) if isinstance(data, dict) else str(data)
    except Exception:
        log_entry = body.decode("utf-8", errors="replace")

    log_entry = str(log_entry)[:10_000]
    if Config.REDACT_LOGS:
        log_entry, _ = redact(log_entry)

    await manager.broadcast({
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "content": log_entry,
    })
    return {"status": "ok"}


class AnalyzeRequest(BaseModel):
    raw_logs: str

    fast_model: str = Config.MODEL_FAST
    smart_model: str = Config.MODEL_REASONING
    reasoning_model: Optional[str] = None
    generation_model: Optional[str] = None

    fast_temp: float = 0.1
    reasoning_temp: float = 0.2
    generation_temp: float = 0.3

    fast_max_tokens: int = 2000
    reasoning_max_tokens: int = 4000
    generation_max_tokens: int = 6000

    jira_mock: bool = Config.JIRA_MOCK_MODE
    notif_mock: bool = Config.NOTIFICATION_MOCK_MODE

    # Repeat incidents inside the TTL reuse the Jira ticket and suppress the alert.
    dedup: bool = Config.DEDUP_ENABLED
    # Hold Jira/alerts for P1/P2 until POST /approve/{request_id}.
    require_approval: bool = Config.REQUIRE_APPROVAL
    # Mask secrets/PII in the log before it reaches an LLM.
    redact: bool = Config.REDACT_LOGS

    source: Optional[str] = "api"

    provider: str = "openrouter"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


class ApprovalDecision(BaseModel):
    approve: bool = True


def _chat_llm(model: str, temperature: float, max_tokens: int, api_key: str, base_url: str) -> ChatOpenAI:
    if not model or not model.strip():
        raise HTTPException(status_code=400, detail="model names cannot be empty")
    return ChatOpenAI(
        model=model.strip(),
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _build_request_graph(payload: AnalyzeRequest):
    api_key = payload.api_key or Config.OPENROUTER_API_KEY
    base_url = validate_base_url(payload.base_url) if payload.base_url else Config.OPENROUTER_BASE_URL
    reasoning_model = payload.reasoning_model or payload.smart_model
    generation_model = payload.generation_model or Config.MODEL_GENERATION

    fast_llm = _chat_llm(payload.fast_model, payload.fast_temp, payload.fast_max_tokens, api_key, base_url)
    reasoning_llm = _chat_llm(reasoning_model, payload.reasoning_temp, payload.reasoning_max_tokens, api_key, base_url)
    generation_llm = _chat_llm(generation_model, payload.generation_temp, payload.generation_max_tokens, api_key, base_url)

    return build_graph(
        classifier_fn=partial(_classifier_with_llm, llm=fast_llm),
        severity_fn=partial(_severity_with_llm, llm=fast_llm),
        root_cause_fn=partial(_root_cause_with_llm, llm=reasoning_llm),
        remediation_fn=partial(_remediation_with_llm, llm=reasoning_llm),
        cookbook_fn=partial(_cookbook_with_llm, llm=generation_llm),
        jira_fn=partial(jira_node, mock_mode=payload.jira_mock, dedup=payload.dedup),
        notification_fn=partial(notification_node, mock_mode=payload.notif_mock, dedup=payload.dedup),
    )


# Thin named wrappers (rather than raw partial(classifier_node, llm=...))
# so LangGraph node names in tracebacks/logs stay readable.
def _classifier_with_llm(state, llm):
    from devops_agents import classifier_node
    return classifier_node(state, llm=llm)


def _severity_with_llm(state, llm):
    from devops_agents import severity_node
    return severity_node(state, llm=llm)


def _root_cause_with_llm(state, llm):
    from devops_agents import root_cause_node
    return root_cause_node(state, llm=llm)


def _remediation_with_llm(state, llm):
    from devops_agents import remediation_node
    return remediation_node(state, llm=llm)


def _cookbook_with_llm(state, llm):
    from devops_agents import cookbook_node
    return cookbook_node(state, llm=llm)


# ── Pending human approvals (in memory; lost on restart) ──────────────────

_pending: dict = {}
_pending_lock = threading.Lock()
_MAX_PENDING = 100


def _purge_pending(now: Optional[float] = None) -> None:
    now = time.time() if now is None else now
    ttl = Config.APPROVAL_TTL_MINUTES * 60
    with _pending_lock:
        for rid in [r for r, e in _pending.items() if now - e["created"] > ttl]:
            del _pending[rid]
        while len(_pending) > _MAX_PENDING:
            del _pending[min(_pending, key=lambda r: _pending[r]["created"])]


def _sse(obj) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.get("/health")
def health():
    connections = [
        {"name": "OpenRouter", "status": "green" if Config.openrouter_configured() else "red"},
        {"name": "LangSmith", "status": "green" if Config.langsmith_configured() else "red"},
        {"name": "JIRA", "status": "green" if (Config.jira_configured() and not Config.JIRA_MOCK_MODE) else "red"},
        {"name": "n8n", "status": "green" if (Config.n8n_webhook_configured() and not Config.NOTIFICATION_MOCK_MODE) else "red"},
        {"name": "Slack", "status": "green" if (Config.slack_webhook_configured() and not Config.NOTIFICATION_MOCK_MODE) else "red"},
    ]
    return {
        "status": "ok",
        "service": "devops-api",
        "connections": connections,
        "settings": {
            "auth_required": bool(Config.API_AUTH_TOKEN),
            "redaction": Config.REDACT_LOGS,
            "dedup": Config.DEDUP_ENABLED,
            "approval_gate_default": Config.REQUIRE_APPROVAL,
        },
    }


@app.get("/samples/{name}", response_class=PlainTextResponse)
def get_sample(name: str):
    """A bundled sample log (data/sample_logs/<name>.log)."""
    if not re.fullmatch(r"[a-z0-9_-]{1,60}", name):
        raise HTTPException(status_code=404, detail="Unknown sample")
    path = SAMPLES_DIR / f"{name}.log"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Unknown sample")
    return path.read_text(encoding="utf-8")


@app.post(
    "/analyze",
    dependencies=[Depends(require_auth), Depends(rate_limit("analyze", "RATE_LIMIT_PER_MIN"))],
)
async def analyze_logs(payload: AnalyzeRequest):
    if not (payload.api_key or Config.openrouter_configured()):
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY not set")
    if not payload.raw_logs.strip():
        raise HTTPException(status_code=400, detail="raw_logs cannot be empty")
    if len(payload.raw_logs) > Config.MAX_LOG_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"raw_logs exceeds the {Config.MAX_LOG_CHARS}-character limit",
        )

    request_graph = _build_request_graph(payload)   # validates base_url / model names (HTTP 400)

    raw_logs, redactions = (redact(payload.raw_logs) if payload.redact else (payload.raw_logs, {}))
    raw_logs, injection_lines = neutralize_injection(raw_logs)

    request_id = str(uuid.uuid4())
    initial_state = base_state(
        raw_logs=raw_logs,
        metadata={
            "source": payload.source,
            "runner": "fastapi",
            "request_id": request_id,
            "require_approval": payload.require_approval,
        },
    )

    def event_generator():
        try:
            yield _sse({"request": {
                "request_id": request_id,
                "redactions": redactions,
                "injection_suspected": bool(injection_lines),
                "require_approval": payload.require_approval,
            }})
            final = dict(initial_state)
            for update in request_graph.stream(initial_state):
                final = apply_update(final, update)
                yield _sse(update)

            if approval_router(final) == "hold":
                _purge_pending()
                with _pending_lock:
                    _pending[request_id] = {
                        "state": final,
                        "created": time.time(),
                        "jira_mock": payload.jira_mock,
                        "notif_mock": payload.notif_mock,
                        "dedup": payload.dedup,
                    }
                yield _sse({"approval": {
                    "status": "pending",
                    "request_id": request_id,
                    "expires_in_s": int(Config.APPROVAL_TTL_MINUTES * 60),
                }})
            yield "data: [DONE]\n\n"
        except Exception as e:
            # Never echo raw exception text: it can carry request details or key fragments.
            yield _sse({"error": redact(f"{type(e).__name__}: {e}")[0][:300]})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post(
    "/approve/{request_id}",
    dependencies=[Depends(require_auth), Depends(rate_limit("approve", "RATE_LIMIT_PER_MIN"))],
)
def approve_run(request_id: str, decision: ApprovalDecision = ApprovalDecision()):
    """Release (approve=true) or discard (approve=false) the Jira ticket and
    alert for a P1/P2 run that was held for human approval."""
    _purge_pending()
    with _pending_lock:
        entry = _pending.pop(request_id, None)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="No pending approval with that id (it expired, was already decided, or the server restarted)",
        )
    if not decision.approve:
        return {"request_id": request_id, "approval_status": "rejected", "jira_tickets": [], "notifications_sent": []}

    state = {**entry["state"], "approval_status": "approved"}
    steps = (
        partial(jira_node, mock_mode=entry["jira_mock"], dedup=entry["dedup"]),
        partial(notification_node, mock_mode=entry["notif_mock"], dedup=entry["dedup"]),
    )
    for step in steps:
        state = apply_update(state, {"step": step(state)})
    return {
        "request_id": request_id,
        "approval_status": "approved",
        "jira_tickets": state.get("jira_tickets", []),
        "notifications_sent": state.get("notifications_sent", []),
        "pipeline_status": state.get("pipeline_status", {}),
    }


# Serve the built React dashboard from this same process/port. Registered
# last so it only catches paths the routes above don't handle. This is a
# manual catch-all (rather than StaticFiles(html=True) mounted at "/")
# because StaticFiles only serves index.html for the exact root path, not
# for React Router client-side routes like /dashboard/analytics — those
# have no matching file on disk and must also fall back to index.html so
# the SPA's own router can take over. Tolerates a missing build (e.g.
# before `npm run build` has been run) by simply not registering the route.
_frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    _dist_root = _frontend_dist.resolve()

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Only ever serve files that resolve to a location inside frontend/dist:
        # a request path like "../../.env" must fall back to the SPA shell, not
        # read files elsewhere on disk.
        if full_path:
            try:
                candidate = (_dist_root / full_path).resolve()
                if candidate.is_file() and candidate.is_relative_to(_dist_root):
                    return FileResponse(candidate)
            except (ValueError, OSError):
                pass
        return FileResponse(_dist_root / "index.html")
