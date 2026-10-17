import pytest

from devops_parsers import build_slack_blocks, parse_log_type, parse_severity_response
from devops_state import apply_update, base_state


# ── LOG_TYPE label ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,label", [
    ("body\nLOG_TYPE: database", "database"),
    ("body\n**LOG_TYPE:** Kubernetes\n", "kubernetes"),
    ("body\n- LOG_TYPE: nginx", "nginx"),
    ("body\nLOG_TYPE: mixed (several systems)", "mixed"),
    ("body\nLog Type: cloudwatch", "cloudwatch"),
])
def test_log_type_label_is_parsed_and_removed(text, label):
    parsed, cleaned = parse_log_type(text)
    assert parsed == label
    assert "log_type" not in cleaned.lower() and cleaned.strip().endswith("body")


@pytest.mark.parametrize("text", ["no label", "body\nLOG_TYPE: other", "body\nLOG_TYPE: unknown", "body\nLOG_TYPE: banana", ""])
def test_unusable_labels_return_none_so_the_heuristic_applies(text):
    assert parse_log_type(text)[0] is None


def test_only_the_last_label_line_counts():
    assert parse_log_type("LOG_TYPE: nginx\nmore text\nLOG_TYPE: database")[0] == "database"


# ── severity corner cases ────────────────────────────────────────────────────

def test_inline_critical_issues_after_the_key_are_captured():
    parsed = parse_severity_response("SEVERITY: P2\nRATIONALE: x\nCRITICAL_ISSUES: db pool exhausted")
    assert [i["title"] for i in parsed["critical_issues"]] == ["db pool exhausted"]


def test_missing_rationale_gets_a_neutral_default_when_severity_was_found():
    assert parse_severity_response("SEVERITY: P1")["rationale"] == "No rationale provided"


# ── Slack blocks ─────────────────────────────────────────────────────────────

def test_slack_blocks_show_ticket_keys_and_mark_existing_ones():
    blocks = build_slack_blocks("P1", "database", "r", ["issue"], jira_tickets=[{"key": "OPS-1"}, {"key": "OPS-2", "duplicate": True}])
    fields = " ".join(f["text"] for f in blocks[1]["fields"])
    assert "OPS-1" in fields and "OPS-2 (existing)" in fields


def test_slack_blocks_say_none_when_there_is_no_ticket():
    blocks = build_slack_blocks("P3", "application", "r", [])
    assert "*Jira:* none" in " ".join(f["text"] for f in blocks[1]["fields"])


# ── stream-update merging ────────────────────────────────────────────────────

def test_apply_update_follows_the_graph_reducers():
    state = base_state("log", {})
    state = apply_update(state, {"classifier": {"log_summary": "s", "pipeline_status": {"classifier": {"status": "done"}}}})
    state = apply_update(state, {"severity": {"severity": "P1", "critical_issues": [{"title": "a"}],
                                              "pipeline_status": {"severity": {"status": "done"}}}})
    state = apply_update(state, {"jira": {"jira_tickets": [{"key": "OPS-1"}], "errors": ["e1"]}})
    state = apply_update(state, {"notification": {"errors": ["e2"]}})

    assert state["log_summary"] == "s" and state["severity"] == "P1"
    assert set(state["pipeline_status"]) == {"classifier", "severity"}      # merged, not replaced
    assert state["critical_issues"] == [{"title": "a"}]
    assert state["jira_tickets"] == [{"key": "OPS-1"}] and state["errors"] == ["e1", "e2"]


def test_apply_update_does_not_mutate_its_input_and_ignores_non_dict_outputs():
    state = base_state("log", {})
    merged = apply_update(state, {"x": {"errors": ["boom"]}, "y": None})
    assert state["errors"] == [] and merged["errors"] == ["boom"]
