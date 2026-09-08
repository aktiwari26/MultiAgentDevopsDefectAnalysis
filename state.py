"""Shared state schema passed between LangGraph nodes."""
from typing import TypedDict


class Issue(TypedDict):
    id: str
    category: str
    severity: str  # critical | high | medium | low
    service: str
    count: int
    message: str


class Remediation(TypedDict):
    issue_id: str
    fix: str
    rationale: str
    steps: list[str]


class IntegrationResult(TypedDict, total=False):
    status: str  # "sent" | "skipped" | "error" | "no_op"
    detail: str
    items: list[dict]  # e.g. created Jira tickets, or per-issue send outcomes
    channels: dict  # per-channel breakdown, e.g. {"slack": {...}, "n8n": {...}}


class IncidentState(TypedDict, total=False):
    log_content: str
    issues: list[Issue]
    remediations: list[Remediation]
    notification_result: IntegrationResult
    jira_result: IntegrationResult
    checklist_md: str
    errors: list[str]
