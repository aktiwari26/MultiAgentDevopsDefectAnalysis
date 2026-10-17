"""LangGraph orchestrator for the 7-agent DevOps pipeline:

  START -> classifier -> severity -> root_cause -> remediation -> cookbook
                                                                     |
                                           approval gate: proceed ---+--- hold (P1/P2 awaiting approval)
                                                                     v              |
                                                      jira -> notification -> END   v
                                                                                   END

Root Cause and Remediation run for every severity. Severity only gates the
integrations: the Jira node files a ticket for P1/P2 and skips itself otherwise.

Jira runs before Notification (not in parallel) so the alert can carry the
ticket key. When a run asks for human approval (metadata.require_approval) and
the severity is P1/P2, the graph stops after the runbook with
approval_status="pending"; api/main.py resumes it via POST /approve/{request_id}.

"""
from __future__ import annotations
from typing import Literal

from langgraph.graph import StateGraph, START, END

from devops_state import DevOpsState


def approval_router(state: DevOpsState) -> Literal["proceed", "hold"]:
    """Hold the integrations only when this run needs a human approval that
    has not been given yet (severity node sets approval_required=True and
    approval_status="pending" for P1/P2 when require_approval is on)."""
    if state.get("approval_required") and state.get("approval_status") == "pending":
        return "hold"
    return "proceed"


def build_graph(
    classifier_fn=None,
    severity_fn=None,
    root_cause_fn=None,
    remediation_fn=None,
    cookbook_fn=None,
    jira_fn=None,
    notification_fn=None,
):
    """Node functions default to the production implementations in
    devops_agents. Pass custom functions to override any subset (used by
    tests, and by api/main.py to bind per-request LLMs/credentials)."""
    if classifier_fn is None:
        from devops_agents import classifier_node as classifier_fn
    if severity_fn is None:
        from devops_agents import severity_node as severity_fn
    if root_cause_fn is None:
        from devops_agents import root_cause_node as root_cause_fn
    if remediation_fn is None:
        from devops_agents import remediation_node as remediation_fn
    if cookbook_fn is None:
        from devops_agents import cookbook_node as cookbook_fn
    if jira_fn is None:
        from devops_agents import jira_node as jira_fn
    if notification_fn is None:
        from devops_agents import notification_node as notification_fn

    builder = StateGraph(DevOpsState)

    builder.add_node("classifier", classifier_fn)
    builder.add_node("severity", severity_fn)
    builder.add_node("root_cause", root_cause_fn)
    builder.add_node("remediation", remediation_fn)
    builder.add_node("cookbook", cookbook_fn)
    builder.add_node("jira", jira_fn)
    builder.add_node("notification", notification_fn)

    builder.add_edge(START, "classifier")
    builder.add_edge("classifier", "severity")

    builder.add_edge("severity", "root_cause")
    builder.add_edge("root_cause", "remediation")
    builder.add_edge("remediation", "cookbook")

    builder.add_conditional_edges("cookbook", approval_router, {"proceed": "jira", "hold": END})
    builder.add_edge("jira", "notification")
    builder.add_edge("notification", END)

    return builder.compile()


EXPECTED_NODES = {
    "classifier",
    "severity",
    "root_cause",
    "remediation",
    "cookbook",
    "jira",
    "notification",
}
EXPECTED_NODE_COUNT = len(EXPECTED_NODES)
