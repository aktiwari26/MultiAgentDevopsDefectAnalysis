"""Pure parsing/formatting helpers for the DevOps pipeline: log-type
detection, severity-response parsing, and the Slack Block Kit builder.

No I/O, no LLM calls — safe to unit test directly.
"""
from __future__ import annotations
import re
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


_MD_NOISE = re.compile(r"[*`#>]+")
_SEVERITY_LINE = re.compile(r"^severity\s*:\s*(.*)$", re.IGNORECASE)
_RATIONALE_LINE = re.compile(r"^rationale\s*:\s*(.*)$", re.IGNORECASE)
_ISSUES_LINE = re.compile(r"^critical[_ ]issues\s*:", re.IGNORECASE)
_BULLET = re.compile(r"^(?:[-*•]|\d+[.)])\s+")
_P_LEVEL = re.compile(r"\bP([1-4])\b", re.IGNORECASE)


def parse_severity_response(response_text: str) -> dict:
    """Parse the SEVERITY:/RATIONALE:/CRITICAL_ISSUES: structured text the
    severity_prompt asks the LLM for.

    Tolerates the formatting models commonly add (markdown bold/headings/
    code fences, leading bullets, any key casing). If no P1-P4 level can be
    found it fails safe to P2 rather than P3, so a real incident is never
    silently downgraded because the model's formatting was unexpected."""
    severity = "P2"
    rationale = "Severity could not be parsed from the model response; defaulted to P2 for safety"
    found_severity = False
    critical_issues: list[dict] = []

    if not response_text:
        return {"severity": severity, "rationale": rationale, "critical_issues": critical_issues}

    parsing_issues = False

    for raw_line in response_text.strip().splitlines():
        raw = raw_line.strip()
        line = _MD_NOISE.sub("", raw).strip()
        line = re.sub(r"^(?:[-•]|\d+[.)])\s+", "", line)

        if not found_severity and (m := _SEVERITY_LINE.match(line)):
            level = _P_LEVEL.search(m.group(1))
            if level:
                severity = f"P{level.group(1)}"
                found_severity = True
        elif m := _RATIONALE_LINE.match(line):
            rationale = m.group(1).strip() or rationale
        elif _ISSUES_LINE.match(line):
            parsing_issues = True
            inline = line.split(":", 1)[1].strip()
            if inline and inline.lower() != "none":
                critical_issues.append({"title": inline, "severity": severity})
        elif parsing_issues and _BULLET.match(raw):
            issue = _MD_NOISE.sub("", _BULLET.sub("", raw)).strip()
            if issue and issue.lower().rstrip(".") != "none":
                critical_issues.append({"title": issue, "severity": severity})

    if found_severity and rationale.startswith("Severity could not be parsed"):
        rationale = "No rationale provided"

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
