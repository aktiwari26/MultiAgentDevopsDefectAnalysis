from config import Config
from dedup import DedupStore


def make_issue(issue_id, severity):
    return {
        "id": issue_id,
        "category": "Database",
        "severity": severity,
        "service": "db",
        "count": 1,
        "message": "Connection refused",
    }


def configure_jira(monkeypatch):
    monkeypatch.setattr(Config, "JIRA_BASE_URL", "https://example.atlassian.net")
    monkeypatch.setattr(Config, "JIRA_EMAIL", "bot@example.com")
    monkeypatch.setattr(Config, "JIRA_API_TOKEN", "token")
    monkeypatch.setattr(Config, "JIRA_PROJECT_KEY", "OPS")
    monkeypatch.setattr(Config, "JIRA_TICKET_SEVERITIES", {"critical", "high"})


def test_skipped_when_not_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "JIRA_BASE_URL", "")
    from agents.jira_agent import JiraAgent

    result = JiraAgent(DedupStore(path=str(tmp_path / "d.json"))).run([make_issue("ISSUE-1", "critical")], [])
    assert result["status"] == "skipped"


def test_no_op_when_no_severity_matches(monkeypatch, tmp_path):
    configure_jira(monkeypatch)
    from agents.jira_agent import JiraAgent

    result = JiraAgent(DedupStore(path=str(tmp_path / "d.json"))).run([make_issue("ISSUE-1", "low")], [])
    assert result["status"] == "no_op"
    assert "No critical/high" in result["detail"]


def test_creates_ticket_for_critical_issue(monkeypatch, tmp_path):
    configure_jira(monkeypatch)

    class FakeResponse:
        status_code = 201

        def json(self):
            return {"key": "OPS-42"}

    monkeypatch.setattr("agents.jira_agent.requests.post", lambda *a, **k: FakeResponse())

    from agents.jira_agent import JiraAgent

    result = JiraAgent(DedupStore(path=str(tmp_path / "d.json"))).run([make_issue("ISSUE-1", "critical")], [])
    assert result["status"] == "sent"
    assert result["items"][0]["key"] == "OPS-42"
    assert "OPS-42" in result["items"][0]["url"]


def test_per_ticket_error_does_not_block_others(monkeypatch, tmp_path):
    configure_jira(monkeypatch)

    class OkResponse:
        status_code = 201

        def json(self):
            return {"key": "OPS-1"}

    class FailResponse:
        status_code = 400
        text = "invalid project key"

    responses = iter([OkResponse(), FailResponse()])
    monkeypatch.setattr("agents.jira_agent.requests.post", lambda *a, **k: next(responses))

    from agents.jira_agent import JiraAgent

    issues = [make_issue("ISSUE-1", "critical"), make_issue("ISSUE-2", "high")]
    result = JiraAgent(DedupStore(path=str(tmp_path / "d.json"))).run(issues, [])

    assert result["status"] == "error"
    keys = [item.get("key") for item in result["items"] if "key" in item]
    errors = [item for item in result["items"] if "error" in item]
    assert keys == ["OPS-1"]
    assert len(errors) == 1
