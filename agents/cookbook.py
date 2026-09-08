"""Cookbook agent — UC-4, UC-5. Always runs as the terminal node,
regardless of which branch the graph took, and never depends on
Slack/Jira output."""
from state import Issue, Remediation

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class CookbookAgent:
    def run(self, issues: list[Issue], remediations: list[Remediation]) -> str:
        if not issues:
            return (
                "# Incident Checklist\n\n"
                "No actionable issues detected. Log is clean.\n"
            )

        remediation_by_id = {r["issue_id"]: r for r in remediations}
        ordered = sorted(issues, key=lambda i: SEVERITY_ORDER.get(i["severity"], 99))

        lines = ["# Incident Checklist", ""]
        for issue in ordered:
            remediation = remediation_by_id.get(issue["id"])
            lines.append(
                f"## [{issue['severity'].upper()}] {issue['category']} — {issue['service']} "
                f"(x{issue['count']})"
            )
            lines.append(f"{issue['message']}")
            lines.append("")
            if remediation:
                lines.append(f"**Fix:** {remediation['fix']}")
                lines.append(f"**Rationale:** {remediation['rationale']}")
                lines.append("")
                for step in remediation["steps"]:
                    lines.append(f"- [ ] {step}")
            else:
                lines.append("- [ ] Manual investigation required.")
            lines.append("")

        return "\n".join(lines)
