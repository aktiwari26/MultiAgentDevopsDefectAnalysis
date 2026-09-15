"""Pure parsing/formatting helpers for the DevOps pipeline: log-type
detection, severity-response parsing, and the Slack Block Kit builder.

No I/O, no LLM calls — safe to unit test directly.
"""
from __future__ import annotations
from datetime import datetime

_LOG_TYPE_RULES: list[tuple[list[str], str]] = [
    (["crashloopbackoff", "kubelet", "kubernetes", "kubectl", "k8s", "pod/", "evicted", "livenessprobe", "readinessprobe", "replicaset", "statefulset", "daemonset", "kube-apiserver"], "kubernetes"),
    (["nginx", "upstream timed out", "upstream server", "no live upstreams", "502 bad gateway", "location /", "access.log", "error.log", "client_max_body", "proxy_pass", "proxy_read_timeout"], "nginx"),
    (["cloudwatch", "cloudwatch alarm", "alarm state change", "alarmname", "metricname", "awslogs", "aws/lambda", "loggroup", "logstream", "aws/rds", "aws/ec2", "aws/ecs", "cloudtrail"], "cloudwatch"),
    (["traceback", "exception", "assertionerror", "typeerror", "valueerror", "nullpointerexception", "stacktrace", "at com.", "at org.", "django", "flask", "fastapi", "rails", "unhandled"], "application"),
    (["fatal:", "deadlock", "lock wait timeout", "too many connections", "pg_wal", "postgresql", "mysql error", "sqlite", "ora-", "sql error", "replication lag", "database error", "pg_hba"], "database"),
    (["mixed", "multiple services", "cross-service"], "mixed"),
]

KNOWN_LOG_TYPES = frozenset({"kubernetes", "nginx", "cloudwatch", "application", "database", "mixed"})


def detect_log_type(logs: str) -> str:
    """Heuristic log-type classification. Returns 'unknown' for empty
    input, else the first matching rule's label, else 'mixed'."""
    if not logs:
        return "unknown"
    logs_lower = logs.lower()
    for keywords, label in _LOG_TYPE_RULES:
        if any(kw in logs_lower for kw in keywords):
            return label
    return "mixed"


def parse_severity_response(response_text: str) -> dict:
    """Parse the SEVERITY:/RATIONALE:/CRITICAL_ISSUES: structured text the
    severity_prompt asks the LLM for. Falls back gracefully on malformed
    input (defaults: severity P3, generic rationale, no issues)."""
    severity = "P3"
    rationale = "Unable to determine"
    critical_issues: list[dict] = []

    if not response_text:
        return {"severity": severity, "rationale": rationale, "critical_issues": critical_issues}

    lines = response_text.strip().split("\n")
    parsing_issues = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("SEVERITY:"):
            raw = stripped.split(":", 1)[1].strip()
            for candidate in ("P1", "P2", "P3", "P4"):
                if candidate in raw.upper():
                    severity = candidate
                    break
        elif stripped.startswith("RATIONALE:"):
            rationale = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("CRITICAL_ISSUES:"):
            parsing_issues = True
        elif parsing_issues and stripped.startswith("-"):
            issue = stripped.lstrip("- ").strip()
            if issue and issue.lower() != "none":
                critical_issues.append({"title": issue, "severity": severity})

    return {"severity": severity, "rationale": rationale, "critical_issues": critical_issues}


def severity_requires_approval(severity: str) -> tuple[bool, str]:
    requires = severity in ("P1", "P2")
    status = "pending" if requires else "auto_approved"
    return requires, status


_SEVERITY_EMOJI = {"P1": "\U0001F534", "P2": "\U0001F7E0", "P3": "\U0001F7E1", "P4": "\U0001F7E2"}


def build_slack_blocks(
    severity: str,
    log_type: str,
    severity_rationale: str,
    critical_issues: list,
    max_issues: int = 5,
) -> list[dict]:
    """Build a Slack Block Kit block array for one incident notification."""
    emoji = _SEVERITY_EMOJI.get(severity, "\U0001F534")
    ts_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    issues_text = "\n".join([
        f"• {i.get('title', i) if isinstance(i, dict) else str(i)}"
        for i in (critical_issues or [])[:max_issues]
    ]) or "See full analysis for details."

    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{emoji} DevOps Incident Alert — {severity}"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Severity:* {severity}"},
                {"type": "mrkdwn", "text": f"*Log Type:* {log_type.upper()}"},
                {"type": "mrkdwn", "text": f"*Time:* {ts_str}"},
                {"type": "mrkdwn", "text": f"*Rationale:* {(severity_rationale or 'N/A')[:100]}"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Critical Issues:*\n{issues_text}"},
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "\U0001F916 Auto-generated by *DevOps* Multi-Agent Incident Suite"}
            ],
        },
    ]
