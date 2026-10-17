import pytest

from devops_graph import build_graph, EXPECTED_NODES, EXPECTED_NODE_COUNT


def make_state(**overrides):
    state = {
        "raw_logs": "boom",
        "metadata": {},
        "log_summary": "",
        "log_type": "",
        "severity": "",
        "severity_rationale": "",
        "critical_issues": [],
        "rag_context": [],
        "root_cause_analysis": "",
        "remediation_plan": "",
        "cookbook": "",
        "approval_required": False,
        "approval_status": "pending",
        "jira_tickets": [],
        "notifications_sent": [],
        "pipeline_status": {},
        "errors": [],
    }
    state.update(overrides)
    return state


def fake_classifier(state):
    return {"log_summary": "classified summary", "log_type": "application",
            "pipeline_status": {"classifier": {"status": "done", "elapsed_s": 0.1}}}


def make_fake_severity(severity):
    def _fake(state):
        return {
            "severity": severity,
            "severity_rationale": "test rationale",
            "critical_issues": [{"title": "issue A", "severity": severity}],
            "approval_required": severity in ("P1", "P2"),
            "approval_status": "pending" if severity in ("P1", "P2") else "auto_approved",
            "pipeline_status": {"severity": {"status": "done", "elapsed_s": 0.1}},
        }
    return _fake


def fake_root_cause(state):
    return {"root_cause_analysis": "the real root cause is X" * 3, "rag_context": ["kb snippet"],
            "pipeline_status": {"root_cause": {"status": "done", "elapsed_s": 0.1}}}


def fake_remediation(state):
    return {"remediation_plan": "do these steps to fix it" * 3,
            "pipeline_status": {"remediation": {"status": "done", "elapsed_s": 0.1}}}


def fake_cookbook(state):
    return {"cookbook": "runbook contents go here" * 3,
            "pipeline_status": {"cookbook": {"status": "done", "elapsed_s": 0.1}}}


def fake_jira(state):
    severity = state.get("severity")
    if severity in ("P3", "P4"):
        return {"jira_tickets": [], "pipeline_status": {"jira": {"status": "skipped"}}}
    return {"jira_tickets": [{"key": "OPS-1", "url": "https://x/OPS-1", "mode": "mock"}],
            "pipeline_status": {"jira": {"status": "done", "elapsed_s": 0.1}}}


def fake_notification(state):
    return {"notifications_sent": [{"channel": "slack", "status": "delivered_mock"}],
            "pipeline_status": {"notification": {"status": "done_mock", "elapsed_s": 0.1}}}


def make_graph(severity="P1"):
    return build_graph(
        classifier_fn=fake_classifier,
        severity_fn=make_fake_severity(severity),
        root_cause_fn=fake_root_cause,
        remediation_fn=fake_remediation,
        cookbook_fn=fake_cookbook,
        jira_fn=fake_jira,
        notification_fn=fake_notification,
    )


def test_graph_topology_has_exactly_seven_nodes():
    app = make_graph()
    node_names = set(app.get_graph().nodes.keys()) - {"__start__", "__end__"}
    assert node_names == EXPECTED_NODES
    assert EXPECTED_NODE_COUNT == 7


def test_p1_runs_full_pipeline_and_fans_out_jira_and_notification():
    app = make_graph(severity="P1")
    result = app.invoke(make_state())

    assert result["severity"] == "P1"
    assert len(result["root_cause_analysis"]) > 10
    assert len(result["remediation_plan"]) > 10
    assert len(result["cookbook"]) > 10
    assert len(result["jira_tickets"]) == 1
    assert len(result["notifications_sent"]) == 1
    assert result["errors"] == []
    assert "classifier" in result["pipeline_status"]
    assert "severity" in result["pipeline_status"]
    assert "cookbook" in result["pipeline_status"]
    assert "jira" in result["pipeline_status"]
    assert "notification" in result["pipeline_status"]


@pytest.mark.parametrize("severity", ["P1", "P2", "P3", "P4"])
def test_root_cause_and_remediation_run_for_every_severity(severity):
    app = make_graph(severity=severity)
    result = app.invoke(make_state())

    assert result["severity"] == severity
    assert len(result["root_cause_analysis"]) > 10
    assert len(result["remediation_plan"]) > 10
    assert len(result["cookbook"]) > 10
    assert len(result["notifications_sent"]) == 1
    for node in ("root_cause", "remediation"):
        assert node in result["pipeline_status"]


@pytest.mark.parametrize("severity,expected_tickets", [("P1", 1), ("P2", 1), ("P3", 0), ("P4", 0)])
def test_jira_is_still_gated_by_severity(severity, expected_tickets):
    app = make_graph(severity=severity)
    result = app.invoke(make_state())
    assert len(result["jira_tickets"]) == expected_tickets


def test_streaming_visits_root_cause_and_remediation_for_p4():
    app = make_graph(severity="P4")
    visited = [next(iter(update)) for update in app.stream(make_state())]
    assert visited.index("severity") < visited.index("root_cause") < visited.index("remediation") < visited.index("cookbook")
