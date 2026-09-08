"""LangGraph orchestrator wiring the five agents into the pipeline
described in the Requirement Dependency Map:

OpenRouter API key
  -> Log Reader Agent (UC-1, UC-5)
       -> issues[] populated?
            NO  -> Cookbook Agent (UC-4, UC-5)
            YES -> Remediation Agent -> remediations[]
                     -> Notification Agent (UC-2)
                     -> Jira Ticket Agent (UC-3)
                     -> Cookbook Agent (UC-4) -> END
"""
from langgraph.graph import StateGraph, END

from agents.cookbook import CookbookAgent
from agents.jira_agent import JiraAgent
from agents.log_reader import LogReaderAgent
from agents.notification import NotificationAgent
from agents.remediation import RemediationAgent
from state import IncidentState

log_reader = LogReaderAgent()
remediation_agent = RemediationAgent()
notification_agent = NotificationAgent()
jira_agent = JiraAgent()
cookbook_agent = CookbookAgent()


def _append_error(state: IncidentState, message: str) -> list[str]:
    errors = list(state.get("errors", []))
    errors.append(message)
    return errors


def log_reader_node(state: IncidentState) -> dict:
    try:
        issues = log_reader.run(state["log_content"])
        return {"issues": issues}
    except Exception as exc:  # noqa: BLE001 - an LLM outage must not crash the app
        return {"issues": [], "errors": _append_error(state, f"Log Reader failed: {exc}")}


def remediation_node(state: IncidentState) -> dict:
    try:
        remediations = remediation_agent.run(state["issues"])
        return {"remediations": remediations}
    except Exception as exc:  # noqa: BLE001
        return {"remediations": [], "errors": _append_error(state, f"Remediation failed: {exc}")}


def notification_node(state: IncidentState) -> dict:
    result = notification_agent.run(state["issues"], state.get("remediations", []))
    return {"notification_result": result}


def jira_node(state: IncidentState) -> dict:
    result = jira_agent.run(state["issues"], state.get("remediations", []))
    return {"jira_result": result}


def cookbook_node(state: IncidentState) -> dict:
    checklist = cookbook_agent.run(state["issues"], state.get("remediations", []))
    return {"checklist_md": checklist}


def route_after_log_reader(state: IncidentState) -> str:
    return "remediation" if state.get("issues") else "cookbook"


def build_graph():
    graph = StateGraph(IncidentState)
    graph.add_node("log_reader", log_reader_node)
    graph.add_node("remediation", remediation_node)
    graph.add_node("notification", notification_node)
    graph.add_node("jira", jira_node)
    graph.add_node("cookbook", cookbook_node)

    graph.set_entry_point("log_reader")
    graph.add_conditional_edges(
        "log_reader",
        route_after_log_reader,
        {"remediation": "remediation", "cookbook": "cookbook"},
    )
    graph.add_edge("remediation", "notification")
    graph.add_edge("notification", "jira")
    graph.add_edge("jira", "cookbook")
    graph.add_edge("cookbook", END)

    return graph.compile()


def run_pipeline(log_content: str) -> IncidentState:
    app = build_graph()
    initial_state: IncidentState = {"log_content": log_content, "errors": []}
    return app.invoke(initial_state)
