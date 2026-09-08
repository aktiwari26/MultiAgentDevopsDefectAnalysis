# Multi-Agent DevOps Incident Analysis Suite

A Streamlit app that runs an uploaded ops log through a LangGraph pipeline
of five agents — Log Reader, Remediation, Notification (Slack + n8n),
Jira Ticket, and Cookbook — producing a prioritized, actionable incident
checklist, with optional automatic notification and Jira ticketing.

This implements UC-1 through UC-6 from the project's use-case spec.
UC-7 (continuous/live monitoring) is intentionally **not** implemented —
per the execution plan it requires a persistence layer and a background
worker that don't exist yet, and is scoped as a separate future epic.

## Architecture

```
OpenRouter API key
  -> Log Reader Agent            (UC-1, UC-5)
       -> issues[] populated?
            NO  -> Cookbook Agent (UC-4, UC-5)
            YES -> Remediation Agent -> remediations[]
                     -> Notification Agent (UC-2, Slack + n8n webhooks)
                     -> Jira Ticket Agent   (UC-3, needs Jira server/email/token/project;
                                             only critical/high severities)
                     -> Cookbook Agent (UC-4) -> END
```

- **Log Reader** (`agents/log_reader.py`) — parses the log via the
  `MODEL_FAST` model, using an explicit severity rubric
  (critical/high/medium/low), grouping repeated occurrences into single
  issues.
- **Remediation** (`agents/remediation.py`) — generates a fix, rationale,
  and step-by-step instructions per issue via the `MODEL_REASONING` model.
- **Notification** (`agents/notification.py`) — posts to a Slack incoming
  webhook and/or an n8n webhook, independently. Skipped (not an error) if
  neither is configured and mock mode is off. Chunks large issue batches
  across multiple Slack messages to stay under Slack's block limits
  (Phase 2 hardening).
- **Jira Ticket** (`agents/jira_agent.py`) — files a ticket per
  critical/high issue via the Jira Cloud REST API, optionally linked to
  an epic and/or sprint. Each ticket is attempted independently, so one
  failure never blocks the rest of the batch.
- **Cookbook** (`agents/cookbook.py`) — always runs, regardless of which
  branch the graph took. Produces the downloadable
  `incident_checklist.md`, sorted by severity.

Every node's failure is caught and recorded rather than raised (UC-6:
degraded mode) — a broken notification or Jira integration never blocks
the core analysis or the checklist.

### Mock modes

Both Jira (`JIRA_MOCK_MODE`) and Notifications (`NOTIFICATION_MOCK_MODE`)
default to **on**, so the full pipeline — including fake Jira ticket keys
and simulated Slack/n8n sends — is exercisable with nothing but an
`OPENROUTER_API_KEY`. Set either to `False` once you have real
credentials for that integration.

### Deduplication (Phase 4)

`dedup.py` hashes each issue's signature (category + service + a
digit-normalized message) and suppresses re-notifying or re-ticketing the
same signature within `DEDUP_WINDOW_HOURS` (default 24h), backed by a
small local JSON file (`.dedup_store.json`). Notification and Jira use
separate namespaces within that file, so notifying an issue in Slack
never suppresses filing its Jira ticket on the same run (and vice versa).

### Observability (LangSmith)

Set `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` to trace every
LLM call and the graph's execution in LangSmith under `LANGCHAIN_PROJECT`.
This is picked up automatically by the `openai`/`langsmith` SDKs from the
process environment — no code changes needed beyond setting the env vars.

## Setup (Phase 0)

1. Copy `.env.example` to `.env` and fill in what you have:
   - `OPENROUTER_API_KEY` — required for every use case. Get one at
     [openrouter.ai](https://openrouter.ai).
   - `LANGCHAIN_TRACING_V2` / `LANGCHAIN_API_KEY` / `LANGCHAIN_PROJECT` —
     optional, enables LangSmith tracing.
   - `JIRA_SERVER` / `JIRA_EMAIL` / `JIRA_API_TOKEN` / `JIRA_PROJECT_KEY`
     — optional, needed only once `JIRA_MOCK_MODE=False`. Confirm your
     project's issue type name (`JIRA_ISSUE_TYPE`, default `Bug`) — it
     varies by project template. `JIRA_EPIC_KEY` links new tickets to an
     epic (via the `parent` field — the team-managed/next-gen Jira Cloud
     convention; classic/company-managed projects use a different custom
     field instead). `JIRA_SPRINT_NAME` is resolved to a sprint id via the
     Jira Agile API at run time; if resolution fails (no board, sprint not
     found), sprint assignment is skipped with a note in the UI rather
     than failing ticket creation. `JIRA_SPRINT_FIELD_ID` (default
     `customfield_10020`) is the Sprint custom field id, which varies by
     Jira instance — override it if tickets get created but land in the
     wrong sprint.
   - `SLACK_WEBHOOK_URL` / `N8N_WEBHOOK_URL` — optional, needed only once
     `NOTIFICATION_MOCK_MODE=False`. Either or both can be set.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Upload a `.log` / `.txt` / `.json` file (try `sample_logs/sample_ops.log`
   for a mix of severities, or `sample_logs/sample_clean.log` for the
   UC-5 "clean log" path).
2. Click **Run Multi-Agent Analysis**.
3. Review issues and remediations, check the **Notifications / Jira** tab
   for integration status, and download `incident_checklist.md` from the
   **Checklist** tab.

## Tests

```bash
pytest
```

Covers dedup signature/window/namespace-isolation logic, checklist
formatting and severity ordering, Jira ticket filtering, mock-mode
ticketing, epic linking, and per-ticket error isolation, Slack/n8n
mock/send/error handling, and graph routing for UC-5 (clean log skips
Remediation/Notification/Jira) and UC-6 (a failed notification doesn't
block Jira or the checklist). Agent calls to the LLM itself aren't
exercised by these tests — `log_reader`/`remediation` are monkeypatched
at the graph level so tests don't require a live API key.

## Known scope boundaries

- **UC-7 (live/continuous monitoring)** is not built. It needs a
  persistence layer (SQLite/Postgres) for incident history/dedup state
  and a background worker independent of Streamlit's request/response
  cycle — both called out in the execution plan as Phase 5, a separate
  project.
- Notification and Jira run **sequentially** (matching the use case's
  described trigger: "Jira, Automatic, after Notification step"), not in
  parallel. The execution plan lists parallelizing them as a Phase 4
  latency optimization if needed later; both nodes are already
  side-effect-independent, so switching `graph.py` to a fan-out/fan-in
  edge is a small change if you want it.
- Epic/sprint linking is best-effort: the `parent` field works for
  team-managed (next-gen) Jira Cloud projects; classic projects and
  non-default Sprint field ids may need the fields adjusted in
  `agents/jira_agent.py`.
