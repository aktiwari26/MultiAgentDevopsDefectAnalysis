"""LangGraph orchestrator for the 7-agent DevOps pipeline:

  START -> classifier -> severity
                            |
              +-------------+-------------+
              | P1/P2 (full_pipeline)      | P3/P4 (summary_only)
              v                            |
          root_cause -> remediation -> cookbook <-+
                                            |
                              +-------------+-------------+
                              v                           v
                            jira                    notification
                              |                           |
                             END                         END

"""
from __future__ import annotations
from typing import Literal

from langgraph.graph import StateGraph, START, END

from devops_state import DevOpsState


def severity_router(state: DevOpsState) -> Literal["full_pipeline", "summary_only"]:
    severity = state.get("severity", "P2")
    return "full_pipeline" if severity in ("P1", "P2") else "summary_only"


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

    builder.add_conditional_edges(
        "severity",
        severity_router,
        {"full_pipeline": "root_cause", "summary_only": "cookbook"},
    )

    builder.add_edge("root_cause", "remediation")
    builder.add_edge("remediation", "cookbook")

    builder.add_edge("cookbook", "jira")
    builder.add_edge("cookbook", "notification")

    builder.add_edge("jira", END)
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
