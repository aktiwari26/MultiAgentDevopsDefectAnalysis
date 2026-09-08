"""Log Reader agent — UC-1, UC-5.

Parses an uploaded log and groups problems into structured issues with a
severity rating. The severity rubric is explicit in the system prompt
(Phase 4, pulled forward per the execution plan's priority order) since
miscalibrated severity silently breaks Jira ticketing (UC-3).
"""
from llm import call_llm, extract_json
from state import Issue

SYSTEM_PROMPT = """You are a Site Reliability Engineering log analyst.

Read the provided log and extract every distinct operational issue. Group
repeated occurrences of the same underlying problem into a single issue
with a count, rather than emitting one entry per line.

Severity rubric (apply consistently — do not guess):
- critical: service is down, data loss, security breach, or customer-facing
  outage in progress right now.
- high: significant degradation (errors, timeouts, failed dependencies)
  that will become critical if not addressed soon, but the service is
  still partially functional.
- medium: recoverable errors, retried operations, resource pressure
  (e.g. elevated latency, connection pool near capacity) that has not yet
  caused user-visible failure.
- low: warnings, deprecations, informational anomalies with no current
  operational impact.

Respond with ONLY a JSON array (no prose, no markdown fence) of objects
with exactly these keys:
  "category": short problem category, e.g. "Database", "Network", "Auth"
  "severity": one of "critical", "high", "medium", "low"
  "service": the service/component name as it appears in the log
  "count": integer, how many times this issue occurred in the log
  "message": a concise (<160 char) representative description

If the log contains no actionable operational issues, respond with an
empty JSON array: []
"""


class LogReaderAgent:
    def run(self, log_content: str) -> list[Issue]:
        raw = call_llm(SYSTEM_PROMPT, log_content, tier="fast")
        parsed = extract_json(raw)
        issues: list[Issue] = []
        for i, item in enumerate(parsed):
            issues.append(
                Issue(
                    id=f"ISSUE-{i + 1}",
                    category=str(item.get("category", "Unknown")),
                    severity=str(item.get("severity", "medium")).lower(),
                    service=str(item.get("service", "unknown")),
                    count=int(item.get("count", 1)),
                    message=str(item.get("message", "")),
                )
            )
        return issues
