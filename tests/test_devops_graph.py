import pytest

from devops_graph import build_graph, approval_router, EXPECTED_NODES, EXPECTED_NODE_COUNT
from devops_parsers import severity_requires_approval


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
        require = bool((state.get("metadata") or {}).get("require_approval"))
        required, status = severity_requires_approval(severity, require)
        return {
            "severity": severity,
            "severity_rationale": "test rationale",
            "critical_issues": [{"title": "issue A", "severity": severity}],
            "approval_required": required,
            "approval_status": status,
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


def test_p1_runs_full_pipeline_then_jira_then_notification():
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


# ── Jira runs before notification, so the alert can carry the ticket ─────────

def test_jira_runs_before_notification_and_alert_sees_the_ticket():
    seen = {}

    def spying_notification(state):
        seen["tickets"] = list(state.get("jira_tickets") or [])
        return fake_notification(state)

    app = build_graph(
        classifier_fn=fake_classifier, severity_fn=make_fake_severity("P1"),
        root_cause_fn=fake_root_cause, remediation_fn=fake_remediation,
        cookbook_fn=fake_cookbook, jira_fn=fake_jira, notification_fn=spying_notification,
    )
    visited = [next(iter(update)) for update in app.stream(make_state())]
    assert visited.index("cookbook") < visited.index("jira") < visited.index("notification")
    assert [t["key"] for t in seen["tickets"]] == ["OPS-1"]


# ── Human approval gate ──────────────────────────────────────────────────────

@pytest.mark.parametrize("required,status,expected", [
    (True, "pending", "hold"),
    (False, "pending", "proceed"),
    (True, "approved", "proceed"),
    (False, "auto_approved", "proceed"),
])
def test_approval_router(required, status, expected):
    assert approval_router({"approval_required": required, "approval_status": status}) == expected


@pytest.mark.parametrize("severity,require,expected", [
    ("P1", True, (True, "pending")),
    ("P2", True, (True, "pending")),
    ("P3", True, (False, "auto_approved")),
    ("P1", False, (False, "auto_approved")),
])
def test_severity_requires_approval_only_when_asked_and_p1_p2(severity, require, expected):
    assert severity_requires_approval(severity, require) == expected


def test_p1_with_require_approval_holds_before_jira_and_notification():
    app = make_graph(severity="P1")
    result = app.invoke(make_state(metadata={"require_approval": True}))

    assert result["approval_status"] == "pending"
    assert len(result["cookbook"]) > 10                    # analysis still completed
    assert result["jira_tickets"] == []
    assert result["notifications_sent"] == []


def test_p3_with_require_approval_is_not_held():
    app = make_graph(severity="P3")
    result = app.invoke(make_state(metadata={"require_approval": True}))
    assert len(result["notifications_sent"]) == 1


def test_p1_without_require_approval_is_not_held():
    app = make_graph(severity="P1")
    result = app.invoke(make_state())
    assert result["approval_status"] == "auto_approved"
    assert len(result["jira_tickets"]) == 1 and len(result["notifications_sent"]) == 1
