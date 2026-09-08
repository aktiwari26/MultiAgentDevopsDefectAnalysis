import os
import time

from dedup import DedupStore, issue_signature


def make_issue(message="Connection refused", category="Database", service="db"):
    return {
        "id": "ISSUE-1",
        "category": category,
        "severity": "high",
        "service": service,
        "count": 3,
        "message": message,
    }


def test_signature_ignores_digits(tmp_path):
    a = make_issue(message="Connection refused after 5000ms")
    b = make_issue(message="Connection refused after 9999ms")
    assert issue_signature(a) == issue_signature(b)


def test_signature_differs_by_service(tmp_path):
    a = make_issue(service="db-primary")
    b = make_issue(service="db-replica")
    assert issue_signature(a) != issue_signature(b)


def test_filter_new_suppresses_within_window(tmp_path):
    store = DedupStore(path=str(tmp_path / "dedup.json"), window_hours=1)
    issue = make_issue()

    fresh, suppressed = store.filter_new([issue])
    assert fresh == [issue]
    assert suppressed == []

    store.mark_all_seen([issue])
    fresh, suppressed = store.filter_new([issue])
    assert fresh == []
    assert suppressed == [issue]


def test_filter_new_allows_after_window_expires(tmp_path):
    store = DedupStore(path=str(tmp_path / "dedup.json"), window_hours=1e-9)
    issue = make_issue()
    store.mark_all_seen([issue])
    time.sleep(0.01)
    fresh, suppressed = store.filter_new([issue])
    assert fresh == [issue]
    assert suppressed == []


def test_store_survives_missing_file(tmp_path):
    store = DedupStore(path=str(tmp_path / "does_not_exist.json"), window_hours=24)
    assert store.seen_recently("whatever") is False


def test_namespaces_isolate_same_file(tmp_path):
    """Notification and Jira share one JSON file but must not share dedup
    state: notifying an issue via Slack must not suppress filing its Jira
    ticket on the same run, and vice versa."""
    path = str(tmp_path / "shared.json")
    notification_store = DedupStore(path=path, window_hours=24, namespace="notification")
    jira_store = DedupStore(path=path, window_hours=24, namespace="jira")
    issue = make_issue()

    notification_store.mark_all_seen([issue])

    fresh, suppressed = jira_store.filter_new([issue])
    assert fresh == [issue]
    assert suppressed == []
