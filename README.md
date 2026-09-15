# Multi-Agent DevOps Incident Analysis Suite

A FastAPI backend running a 7-agent LangGraph pipeline — Classifier,
Severity, Root Cause (RAG-grounded), Remediation, Cookbook, Jira, and
Notification — behind a React dashboard, served from a single process.
Paste or upload a raw log, and the pipeline classifies it, assigns a
`P1`-`P4` severity, produces a root-cause analysis grounded in a small
knowledge base, a remediation plan, an operational runbook, and (for
P1/P2 incidents) a Jira ticket plus a Slack/n8n notification.

## Architecture

```
POST /analyze
  -> Classifier            (log_summary, log_type)
       -> Severity          (severity P1-P4, critical_issues)
            -> P1/P2: Root Cause (RAG) -> Remediation -> Cookbook
            -> P3/P4: Cookbook directly
                 -> Jira          (P1/P2 only; skipped otherwise)
                 -> Notification  (n8n primary, Slack fallback)
```

- **Classifier** (`devops_agents.py::classifier_node`) — structured
  incident report + log-type detection (`devops_parsers.py::detect_log_type`).
- **Severity** — assigns `P1`-`P4` and extracts critical issues
  (`devops_parsers.py::parse_severity_response`).
- **Root Cause** — retrieves grounding context via keyword search
  (`devops_rag.py`) over embedded runbook snippets plus the Markdown files
  in `data/knowledge_base/`, then generates the RCA. Retrieval happens
  even if the LLM call fails, so context is never lost.
- **Remediation** / **Cookbook** — generate the fix plan and an
  operational runbook as markdown text.
- **Jira** — files one ticket per P1/P2 incident via the Jira Cloud REST
  API (mock mode by default), with best-effort epic/sprint linking.
- **Notification** — n8n webhook primary, Slack incoming-webhook
  fallback (mock mode by default).

Every node catches its own exceptions and returns a degraded-but-valid
fallback rather than raising — a broken LLM call, RAG lookup, or
integration never blocks the rest of the pipeline.

### Mock modes

Both `JIRA_MOCK_MODE` and `NOTIFICATION_MOCK_MODE` default to **on**, so
the full pipeline — including fake Jira ticket keys and simulated
Slack/n8n sends — is exercisable with nothing but an `OPENROUTER_API_KEY`.
Set either to `False` once you have real credentials for that
integration.

**Note:** the bundled React dashboard's "Start Analysis" button always
sends `jira_mock: false, notif_mock: false` on every request, regardless
of the server's own mock-mode defaults — so if you've set real Jira/Slack
credentials with mock mode off, clicking it *will* file a real ticket and
send a real message.

### TLS on corporate networks

`config.py` calls `truststore.inject_into_ssl()` at import time so
outbound HTTPS (Slack/Jira/n8n via `requests`, and OpenRouter via
`langchain-openai`) verifies against the OS certificate store — needed on
networks with a TLS-inspecting corporate proxy, where the default
`certifi` bundle won't trust the proxy's root CA.

## Setup

1. Copy `.env.example` to `.env` and fill in what you have:
   - `OPENROUTER_API_KEY` — required. Get one at [openrouter.ai](https://openrouter.ai).
   - `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` —
     optional, reported on `/health` (no tracing calls are wired up yet).
   - `JIRA_SERVER` / `JIRA_EMAIL` / `JIRA_API_TOKEN` / `JIRA_PROJECT_KEY`
     — optional, needed only once `JIRA_MOCK_MODE=False`. `JIRA_EPIC_KEY`
     / `JIRA_SPRINT_NAME` are best-effort linked; sprint resolution is
     skipped (not fatal) if the board/sprint can't be found.
   - `SLACK_WEBHOOK_URL` / `N8N_WEBHOOK_URL` — optional, needed only once
     `NOTIFICATION_MOCK_MODE=False`.
2. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Build the frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   ```
4. Run the app (single process, serves both the API and the built
   dashboard):
   ```bash
   uvicorn api.main:app --port 8000
   ```
   Open `http://localhost:8000/dashboard`.

## Tests

```bash
pytest
```

Covers graph topology/routing (`tests/test_devops_graph.py` — 7 nodes,
P1/P2 vs P3/P4 branching, parallel Jira/Notification fan-out) and
knowledge-base retrieval (`tests/test_devops_rag.py`). Agent LLM calls
aren't exercised directly — tests pass fake node functions into
`build_graph()` so no live API key is required.

## Known scope boundaries

- Root-cause retrieval is keyword search over a small embedded +
  Markdown corpus, not a real vector index — a true LanceDB/LlamaIndex
  pipeline is a possible future enhancement, not required for a working,
  LLM-grounded Root Cause stage.
- No dedup/suppression of repeated incidents across runs.
- The RAG Tuning Studio and Analytics pages in the dashboard are UI-only
  (mock data) — no backend endpoint feeds them yet.
- No live-log-stream ingestion (`/ws/logs`, `/webhook/logs` are not
  implemented).
