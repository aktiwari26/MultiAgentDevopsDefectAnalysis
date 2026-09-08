from state import IntegrationResult
import graph
from graph import build_graph, route_after_log_reader


def make_issue(issue_id="ISSUE-1", severity="critical"):
    return {
        "id": issue_id,
        "category": "Database",
        "severity": severity,
        "service": "db",
        "count": 1,
        "message": "Connection refused",
    }


def test_route_after_log_reader_empty_goes_to_cookbook():
    assert route_after_log_reader({"issues": []}) == "cookbook"


def test_route_after_log_reader_nonempty_goes_to_remediation():
    assert route_after_log_reader({"issues": [make_issue()]}) == "remediation"


def test_uc5_clean_log_skips_remediation_and_integrations(monkeypatch):
    monkeypatch.setattr(graph.log_reader, "run", lambda log_content: [])
    remediation_calls = []
    monkeypatch.setattr(
        graph.remediation_agent, "run", lambda issues: remediation_calls.append(issues) or []
    )

    app = build_graph()
    result = app.invoke({"log_content": "all good", "errors": []})

    assert result["issues"] == []
    assert remediation_calls == []  # remediation node never ran
    assert "slack_result" not in result
    assert "jira_result" not in result
    assert "No actionable issues" in result["checklist_md"]


def test_uc6_slack_failure_does_not_block_jira_or_cookbook(monkeypatch):
    issue = make_issue()
    monkeypatch.setattr(graph.log_reader, "run", lambda log_content: [issue])
    monkeypatch.setattr(
        graph.remediation_agent,
        "run",
        lambda issues: [
            {"issue_id": "ISSUE-1", "fix": "Restart pool", "rationale": "stale conns", "steps": ["Restart"]}
        ],
    )
    monkeypatch.setattr(
        graph.notification_agent,
        "run",
        lambda issues, remediations: IntegrationResult(status="error", detail="Slack API error: rate_limited"),
    )
    monkeypatch.setattr(
        graph.jira_agent,
        "run",
        lambda issues, remediations: IntegrationResult(
            status="sent", detail="Created 1 ticket(s).", items=[{"issue_id": "ISSUE-1", "key": "OPS-1", "url": "x"}]
        ),
    )

    app = build_graph()
    result = app.invoke({"log_content": "boom", "errors": []})

    assert result["slack_result"]["status"] == "error"
    assert result["jira_result"]["status"] == "sent"
    assert "Restart pool" in result["checklist_md"]
