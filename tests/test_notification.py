import sys
import types

import pytest

from config import Config


def make_issue(issue_id="ISSUE-1", severity="high"):
    return {
        "id": issue_id,
        "category": "Database",
        "severity": severity,
        "service": "db",
        "count": 2,
        "message": "Connection refused",
    }


def install_fake_slack_sdk(monkeypatch, post_message):
    class FakeSlackApiError(Exception):
        def __init__(self, message, response):
            super().__init__(message)
            self.response = response

    class FakeWebClient:
        def __init__(self, token):
            self.token = token

        def chat_postMessage(self, **kwargs):
            return post_message(**kwargs)

    slack_sdk_module = types.ModuleType("slack_sdk")
    slack_sdk_module.WebClient = FakeWebClient
    errors_module = types.ModuleType("slack_sdk.errors")
    errors_module.SlackApiError = FakeSlackApiError
    slack_sdk_module.errors = errors_module

    monkeypatch.setitem(sys.modules, "slack_sdk", slack_sdk_module)
    monkeypatch.setitem(sys.modules, "slack_sdk.errors", errors_module)
    return FakeSlackApiError


def test_skipped_when_not_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "SLACK_BOT_TOKEN", "")
    monkeypatch.setattr(Config, "SLACK_CHANNEL", "")
    from agents.notification import NotificationAgent
    from dedup import DedupStore

    result = NotificationAgent(DedupStore(path=str(tmp_path / "d.json"))).run([make_issue()], [])
    assert result["status"] == "skipped"


def test_sends_and_marks_dedup(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "SLACK_BOT_TOKEN", "xoxb-fake")
    monkeypatch.setattr(Config, "SLACK_CHANNEL", "#incidents")
    install_fake_slack_sdk(monkeypatch, lambda **kwargs: {"ts": "123.456"})

    from agents.notification import NotificationAgent
    from dedup import DedupStore

    store = DedupStore(path=str(tmp_path / "d.json"))
    agent = NotificationAgent(store)
    issue = make_issue()

    first = agent.run([issue], [])
    assert first["status"] == "sent"

    second = agent.run([issue], [])
    assert second["status"] == "no_op"


def test_slack_api_error_is_caught_not_raised(monkeypatch, tmp_path):
    monkeypatch.setattr(Config, "SLACK_BOT_TOKEN", "xoxb-fake")
    monkeypatch.setattr(Config, "SLACK_CHANNEL", "#incidents")
    captured = {}

    def raise_error(**kwargs):
        raise captured["error_cls"]("boom", response={"error": "channel_not_found"})

    captured["error_cls"] = install_fake_slack_sdk(monkeypatch, raise_error)

    from agents.notification import NotificationAgent
    from dedup import DedupStore

    result = NotificationAgent(DedupStore(path=str(tmp_path / "d.json"))).run([make_issue()], [])
    assert result["status"] == "error"
    assert "channel_not_found" in result["detail"]
