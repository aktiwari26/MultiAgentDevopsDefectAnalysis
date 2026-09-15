"""FastAPI backend for the DevOps Incident Analysis Suite's React dashboard.

Serves the SSE-streamed 7-agent pipeline (devops_graph.build_graph()) at
POST /analyze, connection health at GET /health, a live log feed at
WS /ws/logs (fed by POST /webhook/logs), and — once built — the React
dashboard itself as static files, all from this single process/port.
Run from the project root: `uvicorn api.main:app --port 8000`.
"""
import json
import uuid
from datetime import datetime, timezone
from functools import partial
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from config import Config
from devops_state import base_state
from devops_graph import build_graph
from devops_agents import jira_node, notification_node

app = FastAPI(title="DevOps API", version="1.0.0")


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
    await manager.connect(websocket)
    try:
        while True:
            # The dashboard's Live Stream tab only receives; it never sends,
            # but we still need to await something to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/webhook/logs")
async def webhook_logs(request: Request):
    """Push one log line to every connected /ws/logs client. Accepts
    {"log": "<line>"} (or any JSON body — falls back to its str()), or a
    raw text body if the request isn't valid JSON at all."""
    try:
        data = await request.json()
        log_entry = data.get("log", str(data)) if isinstance(data, dict) else str(data)
    except Exception:
        log_entry = (await request.body()).decode("utf-8", errors="replace")

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

    source: Optional[str] = "api"

    provider: str = "openrouter"
    api_key: Optional[str] = None
    base_url: Optional[str] = None


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
    base_url = payload.base_url or Config.OPENROUTER_BASE_URL
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
        jira_fn=partial(jira_node, mock_mode=payload.jira_mock),
        notification_fn=partial(notification_node, mock_mode=payload.notif_mock),
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


@app.get("/health")
def health():
    connections = [
        {"name": "OpenRouter", "status": "green" if Config.openrouter_configured() else "red"},
        {"name": "LangSmith", "status": "green" if Config.langsmith_configured() else "red"},
        {"name": "JIRA", "status": "green" if (Config.jira_configured() and not Config.JIRA_MOCK_MODE) else "red"},
        {"name": "n8n", "status": "green" if (Config.n8n_webhook_configured() and not Config.NOTIFICATION_MOCK_MODE) else "red"},
        {"name": "Slack", "status": "green" if (Config.slack_webhook_configured() and not Config.NOTIFICATION_MOCK_MODE) else "red"},
    ]
    return {"status": "ok", "service": "devops-api", "connections": connections}


@app.post("/analyze")
async def analyze_logs(payload: AnalyzeRequest):
    if not (payload.api_key or Config.openrouter_configured()):
        raise HTTPException(status_code=503, detail="OPENROUTER_API_KEY not set")
    if not payload.raw_logs.strip():
        raise HTTPException(status_code=400, detail="raw_logs cannot be empty")

    request_graph = _build_request_graph(payload)
    initial_state = base_state(
        raw_logs=payload.raw_logs,
        metadata={"source": payload.source, "runner": "fastapi", "request_id": str(uuid.uuid4())},
    )

    def event_generator():
        try:
            for update in request_graph.stream(initial_state):
                yield f"data: {json.dumps(update)}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_dist / "index.html")
