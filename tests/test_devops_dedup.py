import json

import devops_dedup as dd

PAY_A = """2026-03-07 02:14:07 ERROR [payment-service] HikariPool-1 - Connection is not available, request timed out after 30000ms.
2026-03-07 02:14:15 FATAL: sorry, too many clients already (db-primary, 100/100 connections in use)
request_id=550e8400-e29b-41d4-a716-446655440000"""

PAY_RECURRENCE = """2026-04-19 11:59:59 ERROR [payment-service] HikariPool-1 - Connection is not available, request timed out after 31000ms.
2026-04-19 11:59:59 FATAL: sorry, too many clients already (db-primary, 99/100 connections in use)
request_id=11111111-2222-3333-4444-555555555555"""

OTHER = "2026-03-07 02:14:07 ERROR [checkout] NullPointerException at CartService.java:88"


def test_fingerprint_ignores_timestamps_ids_and_numbers():
    assert dd.fingerprint(PAY_A) == dd.fingerprint(PAY_RECURRENCE)


def test_fingerprint_distinguishes_different_incidents():
    assert dd.fingerprint(PAY_A) != dd.fingerprint(OTHER)


def test_fingerprint_is_order_and_duplicate_insensitive():
    lines = PAY_A.splitlines()
    assert dd.fingerprint("\n".join(reversed(lines))) == dd.fingerprint("\n".join(lines + lines[:1]))


def test_fingerprint_of_empty_input_is_stable():
    assert dd.fingerprint("") == dd.fingerprint("")


def test_store_round_trip_ticket_and_notified(tmp_path):
    path = str(tmp_path / "store.json")
    fp = dd.fingerprint(PAY_A)

    assert dd.get(fp, path) is None
    dd.update(fp, path, ticket={"key": "OPS-1"})
    assert dd.get(fp, path)["ticket"] == {"key": "OPS-1"}
    assert "notified_at" not in dd.get(fp, path)

    dd.update(fp, path, notified=True)
    entry = dd.get(fp, path)
    assert entry["ticket"] == {"key": "OPS-1"}      # earlier fields survive a later update
    assert "notified_at" in entry and entry["count"] == 2


def test_entries_expire_after_the_ttl(tmp_path):
    path = str(tmp_path / "store.json")
    fp = dd.fingerprint(PAY_A)
    dd.update(fp, path, ticket={"key": "OPS-1"})
    assert dd.get(fp, path, ttl_hours=24) is not None
    assert dd.get(fp, path, ttl_hours=0) is None


def test_update_prunes_expired_entries(tmp_path):
    path = tmp_path / "store.json"
    path.write_text(json.dumps({"old": {"updated_at": 1, "count": 1}}), encoding="utf-8")
    dd.update(dd.fingerprint(PAY_A), str(path), ticket={"key": "OPS-2"})
    assert "old" not in json.loads(path.read_text(encoding="utf-8"))


def test_corrupt_store_file_is_treated_as_empty(tmp_path):
    path = tmp_path / "store.json"
    path.write_text("{not json", encoding="utf-8")
    assert dd.get("anything", str(path)) is None
    dd.update("k", str(path), ticket={"key": "OPS-3"})
    assert dd.get("k", str(path))["ticket"] == {"key": "OPS-3"}
