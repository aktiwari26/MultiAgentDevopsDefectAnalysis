from config import Config
from dedup import DedupStore


def make_issue(issue_id="ISSUE-1", severity="high"):
    return {
        "id": issue_id,
        "category": "Database",
        "severity": severity,
        "service": "db",
        "count": 2,
        "message": "Connection refused",
    }


def configure_mock(monkeypatch, on=True):
    monkeypatch.setattr(Config, "NOTIFICATION_MOCK_MODE", on)
    monkeypatch.setattr(Config, "SLACK_WEBHOOK_URL", "")
    monkeypatch.setattr(Config, "N8N_WEBHOOK_URL", "")


def test_skipped_when_not_configured_and_mock_off(monkeypatch, tmp_path):
    configure_mock(monkeypatch, on=False)
    from agents.notification import NotificationAgent

    result = NotificationAgent(DedupStore(path=str(tmp_path / "d.json"), namespace="notification")).run(
        [make_issue()], []
    )
    assert result["status"] == "skipped"


def test_mock_mode_reports_sent_without_network(monkeypatch, tmp_path):
    configure_mock(monkeypatch, on=True)
    monkeypatch.setattr(Config, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/x")

    from agents.notification import NotificationAgent

    store = DedupStore(path=str(tmp_path / "d.json"), namespace="notification")
    agent = NotificationAgent(store)
    issue = make_issue()

    first = agent.run([issue], [])
    assert first["status"] == "sent"
    assert "MOCK" in first["channels"]["slack"]["detail"]
    assert first["channels"]["n8n"]["status"] == "skipped"

    second = agent.run([issue], [])
    assert second["status"] == "no_op"


def test_slack_webhook_error_is_caught_not_raised(monkeypatch, tmp_path):
    configure_mock(monkeypatch, on=False)
    monkeypatch.setattr(Config, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/x")

    class FailResponse:
        status_code = 404
        text = "channel_not_found"

    monkeypatch.setattr("agents.notification.requests.post", lambda *a, **k: FailResponse())

    from agents.notification import NotificationAgent

    result = NotificationAgent(DedupStore(path=str(tmp_path / "d.json"), namespace="notification")).run(
        [make_issue()], []
    )
    assert result["status"] == "error"
    assert "channel_not_found" in result["channels"]["slack"]["detail"]


def test_n8n_sent_independently_of_slack(monkeypatch, tmp_path):
    configure_mock(monkeypatch, on=False)
    monkeypatch.setattr(Config, "N8N_WEBHOOK_URL", "https://n8n.example.com/webhook/x")

    class OkResponse:
        status_code = 200

    monkeypatch.setattr("agents.notification.requests.post", lambda *a, **k: OkResponse())

    from agents.notification import NotificationAgent

    result = NotificationAgent(DedupStore(path=str(tmp_path / "d.json"), namespace="notification")).run(
        [make_issue()], []
    )
    assert result["status"] == "sent"
    assert result["channels"]["slack"]["status"] == "skipped"
    assert result["channels"]["n8n"]["status"] == "sent"
