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


def store(tmp_path):
    return DedupStore(path=str(tmp_path / "d.json"), namespace="jira")


def test_skipped_when_mock_off_and_not_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "JIRA_MOCK_MODE", False)
    monkeypatch.setattr(Config, "JIRA_SERVER", "")
    from agents.jira_agent import JiraAgent

    result = JiraAgent(store(tmp_path)).run([make_issue("ISSUE-1", "critical")], [])
    assert result["status"] == "skipped"


def test_mock_mode_creates_fake_tickets_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "JIRA_MOCK_MODE", True)
    monkeypatch.setattr(Config, "JIRA_PROJECT_KEY", "OPS")
    from agents.jira_agent import JiraAgent

    agent = JiraAgent(store(tmp_path))
    issue = make_issue("ISSUE-1", "critical")

    first = agent.run([issue], [])
    assert first["status"] == "sent"
    assert first["items"][0]["key"].startswith("OPS-")
    assert first["items"][0]["mock"] is True

    second = agent.run([issue], [])
    assert second["status"] == "no_op"


def test_no_op_when_no_severity_matches(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "JIRA_MOCK_MODE", True)
    from agents.jira_agent import JiraAgent

    result = JiraAgent(store(tmp_path)).run([make_issue("ISSUE-1", "low")], [])
    assert result["status"] == "no_op"
    assert "No critical/high" in result["detail"]


def configure_real_jira(monkeypatch):
    monkeypatch.setattr(Config, "JIRA_MOCK_MODE", False)
    monkeypatch.setattr(Config, "JIRA_SERVER", "https://example.atlassian.net")
    monkeypatch.setattr(Config, "JIRA_EMAIL", "bot@example.com")
    monkeypatch.setattr(Config, "JIRA_API_TOKEN", "token")
    monkeypatch.setattr(Config, "JIRA_PROJECT_KEY", "OPS")
    monkeypatch.setattr(Config, "JIRA_TICKET_SEVERITIES", {"critical", "high"})
    monkeypatch.setattr(Config, "JIRA_EPIC_KEY", "")
    monkeypatch.setattr(Config, "JIRA_SPRINT_NAME", "")


def test_real_mode_creates_ticket_for_critical_issue(monkeypatch, tmp_path):
    configure_real_jira(monkeypatch)

    class FakeResponse:
        status_code = 201

        def json(self):
            return {"key": "OPS-42"}

    monkeypatch.setattr("agents.jira_agent.requests.post", lambda *a, **k: FakeResponse())

    from agents.jira_agent import JiraAgent

    result = JiraAgent(store(tmp_path)).run([make_issue("ISSUE-1", "critical")], [])
    assert result["status"] == "sent"
    assert result["items"][0]["key"] == "OPS-42"
    assert "OPS-42" in result["items"][0]["url"]


def test_real_mode_per_ticket_error_does_not_block_others(monkeypatch, tmp_path):
    configure_real_jira(monkeypatch)

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
    result = JiraAgent(store(tmp_path)).run(issues, [])

    assert result["status"] == "error"
    keys = [item.get("key") for item in result["items"] if "key" in item]
    errors = [item for item in result["items"] if "error" in item]
    assert keys == ["OPS-1"]
    assert len(errors) == 1


def test_epic_link_included_when_configured(monkeypatch, tmp_path):
    configure_real_jira(monkeypatch)
    monkeypatch.setattr(Config, "JIRA_EPIC_KEY", "OPS-1")

    captured = {}

    class FakeResponse:
        status_code = 201

        def json(self):
            return {"key": "OPS-99"}

    def fake_post(url, json=None, **kwargs):
        captured["fields"] = json["fields"]
        return FakeResponse()

    monkeypatch.setattr("agents.jira_agent.requests.post", fake_post)

    from agents.jira_agent import JiraAgent

    JiraAgent(store(tmp_path)).run([make_issue("ISSUE-1", "critical")], [])
    assert captured["fields"]["parent"] == {"key": "OPS-1"}
