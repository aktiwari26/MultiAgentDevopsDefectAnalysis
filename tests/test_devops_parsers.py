import pytest

from devops_parsers import parse_severity_response


@pytest.mark.parametrize("text,expected", [
    ("SEVERITY: P1\nRATIONALE: x", "P1"),
    ("**SEVERITY:** P1\n**RATIONALE:** x", "P1"),
    ("SEVERITY: **P2**\nRATIONALE: x", "P2"),
    ("- SEVERITY: P1\n- RATIONALE: x", "P1"),
    ("### SEVERITY: P2\nRATIONALE: x", "P2"),
    ("Severity: P1\nRationale: x", "P1"),
    ("Sure, here is the triage:\n\nSEVERITY: P1", "P1"),
    ("```\nSEVERITY: P1\nRATIONALE: x\n```", "P1"),
    ("SEVERITY: High (P2)\nRATIONALE: x", "P2"),
    ("SEVERITY: P3 (not P1)\nRATIONALE: x", "P3"),
    ("SEVERITY: P4\nRATIONALE: x", "P4"),
])
def test_severity_level_is_parsed_despite_formatting(text, expected):
    assert parse_severity_response(text)["severity"] == expected


@pytest.mark.parametrize("text", ["", "I think this is bad.", "SEVERITY: unknown"])
def test_unparseable_severity_fails_safe_to_p2(text):
    result = parse_severity_response(text)
    assert result["severity"] == "P2"
    assert "defaulted to P2" in result["rationale"]


def test_critical_issues_are_extracted_from_plain_and_markdown():
    plain = parse_severity_response("SEVERITY: P1\nRATIONALE: x\nCRITICAL_ISSUES:\n- DB down: pool exhausted\n- API 503: upstream")
    assert [i["title"] for i in plain["critical_issues"]] == ["DB down: pool exhausted", "API 503: upstream"]

    md = parse_severity_response("**SEVERITY:** P1\n**CRITICAL_ISSUES:**\n- **DB down**: pool exhausted")
    assert [i["title"] for i in md["critical_issues"]] == ["DB down: pool exhausted"]


@pytest.mark.parametrize("none_form", ["None", "- None", "none."])
def test_none_is_not_reported_as_an_issue(none_form):
    result = parse_severity_response(f"SEVERITY: P3\nRATIONALE: minor\nCRITICAL_ISSUES:\n{none_form}")
    assert result["critical_issues"] == []
