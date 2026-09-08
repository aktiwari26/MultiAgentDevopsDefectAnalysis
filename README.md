# Multi-Agent DevOps Incident Analysis Suite

A Streamlit app that runs an uploaded ops log through a LangGraph pipeline
of five agents — Log Reader, Remediation, Notification (Slack), Jira
Ticket, and Cookbook — producing a prioritized, actionable incident
checklist, with optional automatic Slack notification and Jira ticketing.

This implements UC-1 through UC-6 from the project's use-case spec.
UC-7 (continuous/live monitoring) is intentionally **not** implemented —
per the execution plan it requires a persistence layer and a background
worker that don't exist yet, and is scoped as a separate future epic.

## Architecture

```
Anthropic API key
  -> Log Reader Agent            (UC-1, UC-5)
       -> issues[] populated?
            NO  -> Cookbook Agent (UC-4, UC-5)
            YES -> Remediation Agent -> remediations[]
                     -> Notification Agent (UC-2, needs Slack token + channel)
                     -> Jira Ticket Agent   (UC-3, needs Jira URL/email/token/project;
                                             only critical/high severities)
                     -> Cookbook Agent (UC-4) -> END
```

- **Log Reader** (`agents/log_reader.py`) — parses the log with Claude
  using an explicit severity rubric (critical/high/medium/low), grouping
  repeated occurrences into single issues.
- **Remediation** (`agents/remediation.py`) — generates a fix, rationale,
  and step-by-step instructions per issue.
- **Notification** (`agents/notification.py`) — posts a Slack Block Kit
  summary. Skipped (not an error) if Slack isn't configured. Chunks large
  issue batches across multiple messages to stay under Slack's block
  limits (Phase 2 hardening).
- **Jira Ticket** (`agents/jira_agent.py`) — files a ticket per
  critical/high issue via the Jira Cloud REST API. Each ticket is
  attempted independently, so one failure never blocks the rest of the
  batch.
- **Cookbook** (`agents/cookbook.py`) — always runs, regardless of which
  branch the graph took. Produces the downloadable
  `incident_checklist.md`, sorted by severity.

Every node's failure is caught and recorded rather than raised (UC-6:
degraded mode) — a broken Slack or Jira integration never blocks the
core analysis or the checklist.

### Deduplication (Phase 4)

`dedup.py` hashes each issue's signature (category + service + a
digit-normalized message) and suppresses re-notifying or re-ticketing the
same signature within `DEDUP_WINDOW_HOURS` (default 24h), backed by a
small local JSON file (`.dedup_store.json`).

## Setup (Phase 0)

1. Copy `.env.example` to `.env` and fill in what you have:
   - `ANTHROPIC_API_KEY` — required for every use case.
   - `SLACK_BOT_TOKEN` / `SLACK_CHANNEL` — optional, enables UC-2. The
     Slack app needs the `chat:write` scope and must be invited to the
     target channel.
   - `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` / `JIRA_PROJECT_KEY`
     — optional, enables UC-3. Confirm your project's issue type name
     (`JIRA_ISSUE_TYPE`, default `Bug`) — it varies by project template.
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
3. Review issues and remediations, check the **Slack / Jira** tab for
   integration status, and download `incident_checklist.md` from the
   **Checklist** tab.

## Tests

```bash
pytest
```

Covers dedup signature/window logic, checklist formatting and severity
ordering, Jira ticket filtering and per-ticket error isolation, Slack
skip/send/error handling, and graph routing for UC-5 (clean log skips
Remediation/Notification/Jira) and UC-6 (a failed Slack post doesn't
block Jira or the checklist). Agent calls to Claude itself aren't
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
