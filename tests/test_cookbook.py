from agents.cookbook import CookbookAgent


def make_issue(issue_id, severity):
    return {
        "id": issue_id,
        "category": "Database",
        "severity": severity,
        "service": "db",
        "count": 1,
        "message": "Connection refused",
    }


def make_remediation(issue_id):
    return {
        "issue_id": issue_id,
        "fix": "Restart the connection pool",
        "rationale": "Stale connections were holding the pool open",
        "steps": ["Restart pool", "Verify health check"],
    }


def test_clean_log_reports_all_clear():
    checklist = CookbookAgent().run([], [])
    assert "No actionable issues detected" in checklist


def test_checklist_sorted_by_severity_and_has_checkboxes():
    issues = [make_issue("ISSUE-1", "low"), make_issue("ISSUE-2", "critical")]
    remediations = [make_remediation("ISSUE-1"), make_remediation("ISSUE-2")]

    checklist = CookbookAgent().run(issues, remediations)

    critical_pos = checklist.index("CRITICAL")
    low_pos = checklist.index("LOW")
    assert critical_pos < low_pos
    assert "- [ ] Restart pool" in checklist


def test_missing_remediation_falls_back_to_manual_investigation():
    issues = [make_issue("ISSUE-1", "high")]
    checklist = CookbookAgent().run(issues, [])
    assert "Manual investigation required" in checklist
