"""State schema for the 7-agent DevOps pipeline (Classifier -> Severity ->
Root Cause -> Remediation -> Cookbook -> {Jira, Notification}), driving the
React dashboard via api/main.py.

TypedDict (not a Pydantic BaseModel) because LangGraph's
Annotated[list, operator.add] reducers require TypedDict to merge partial
node outputs from parallel branches (jira + notification) correctly.
"""
from typing import TypedDict, Annotated
from operator import add


def _merge_pipeline_status(a: dict, b: dict) -> dict:
    """Reducer for pipeline_status: merge so parallel nodes (jira +
    notification) can each write their status without clobbering the other."""
    merged = dict(a)
    merged.update(b)
    return merged


class DevOpsState(TypedDict):
    # -- Input --
    raw_logs: str
    metadata: dict

    # -- Classification (Classifier Agent) --
    log_summary: str
    log_type: str

    # -- Severity (Severity Agent) --
    severity: str
    severity_rationale: str
    critical_issues: Annotated[list, add]

    # -- Root Cause (RCA Agent + RAG) --
    rag_context: Annotated[list, add]
    root_cause_analysis: str

    # -- Remediation (Remediation Agent) --
    remediation_plan: str

    # -- Cookbook (Cookbook Agent) --
    cookbook: str

    # -- Human approval --
    approval_required: bool
    approval_status: str

    # -- JIRA (JIRA Agent) --
    jira_tickets: Annotated[list, add]

    # -- Notifications (Notification Agent) --
    notifications_sent: Annotated[list, add]

    # -- Pipeline metadata --
    pipeline_status: Annotated[dict, _merge_pipeline_status]
    errors: Annotated[list, add]


REQUIRED_INPUT_FIELDS = {"raw_logs", "metadata"}
ALL_STATE_FIELDS = set(DevOpsState.__annotations__.keys())
LIST_FIELDS_WITH_REDUCERS = {
    "critical_issues",
    "rag_context",
    "jira_tickets",
    "notifications_sent",
    "errors",
}
DICT_FIELDS_WITH_REDUCERS = {"pipeline_status"}
FIELDS_WITH_REDUCERS = LIST_FIELDS_WITH_REDUCERS | DICT_FIELDS_WITH_REDUCERS


def base_state(raw_logs: str, metadata: dict) -> dict:
    """Fully-populated initial state for a fresh graph run."""
    return {
        "raw_logs": raw_logs,
        "metadata": metadata,
        "log_summary": "",
        "log_type": "",
        "severity": "",
        "severity_rationale": "",
        "approval_required": False,
        "approval_status": "pending",
        "critical_issues": [],
        "rag_context": [],
        "root_cause_analysis": "",
        "remediation_plan": "",
        "cookbook": "",
        "jira_tickets": [],
        "notifications_sent": [],
        "pipeline_status": {},
        "errors": [],
    }
