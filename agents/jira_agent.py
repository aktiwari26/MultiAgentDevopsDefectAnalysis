"""Jira Ticket agent — UC-3, with UC-6 degraded-mode semantics: each
ticket attempt is isolated, so one failure never blocks the rest of the
batch or the pipeline."""
import requests

from config import Config
from dedup import DedupStore
from state import Issue, Remediation, IntegrationResult


def _build_description(issue: Issue, remediation: Remediation | None) -> dict:
    lines = [issue["message"], ""]
    if remediation:
        lines.append(f"Fix: {remediation['fix']}")
        lines.append(f"Rationale: {remediation['rationale']}")
        if remediation["steps"]:
            lines.append("Remediation steps:")
            lines.extend(f"- {step}" for step in remediation["steps"])
    text = "\n".join(lines)
    # Jira Cloud v3 requires Atlassian Document Format for `description`.
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": paragraph}],
            }
            for paragraph in text.split("\n")
            if paragraph
        ],
    }


class JiraAgent:
    def __init__(self, dedup_store: DedupStore | None = None):
        self.dedup_store = dedup_store or DedupStore()

    def run(self, issues: list[Issue], remediations: list[Remediation]) -> IntegrationResult:
        if not Config.jira_configured():
            return IntegrationResult(status="skipped", detail="Jira not configured.")

        ticket_worthy = [i for i in issues if i["severity"].lower() in Config.JIRA_TICKET_SEVERITIES]
        if not ticket_worthy:
            return IntegrationResult(
                status="no_op",
                detail="No critical/high issues required a ticket.",
            )

        fresh_issues, suppressed = self.dedup_store.filter_new(ticket_worthy)
        if not fresh_issues:
            return IntegrationResult(
                status="no_op",
                detail=f"All {len(suppressed)} ticket-worthy issue(s) already ticketed within the dedup window.",
            )

        remediation_by_id = {r["issue_id"]: r for r in remediations}
        url = f"{Config.JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue"
        auth = (Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)

        created, per_issue_errors, newly_ticketed = [], [], []
        for issue in fresh_issues:
            remediation = remediation_by_id.get(issue["id"])
            payload = {
                "fields": {
                    "project": {"key": Config.JIRA_PROJECT_KEY},
                    "summary": f"[{issue['severity'].upper()}] {issue['category']} — {issue['service']}",
                    "description": _build_description(issue, remediation),
                    "issuetype": {"name": Config.JIRA_ISSUE_TYPE},
                }
            }
            try:
                resp = requests.post(url, json=payload, auth=auth, timeout=15)
                if resp.status_code in (200, 201):
                    key = resp.json().get("key")
                    created.append(
                        {
                            "issue_id": issue["id"],
                            "key": key,
                            "url": f"{Config.JIRA_BASE_URL.rstrip('/')}/browse/{key}",
                        }
                    )
                    newly_ticketed.append(issue)
                else:
                    per_issue_errors.append(
                        {"issue_id": issue["id"], "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
                    )
            except requests.RequestException as exc:
                per_issue_errors.append({"issue_id": issue["id"], "error": str(exc)})

        if newly_ticketed:
            self.dedup_store.mark_all_seen(newly_ticketed)

        if created and not per_issue_errors:
            status = "sent"
        elif created and per_issue_errors:
            status = "error"  # partial failure, still surfaced distinctly in items
        elif per_issue_errors:
            status = "error"
        else:
            status = "no_op"

        detail = f"Created {len(created)} ticket(s)"
        if suppressed:
            detail += f", {len(suppressed)} suppressed as duplicates"
        if per_issue_errors:
            detail += f", {len(per_issue_errors)} failed"
        detail += "."

        return IntegrationResult(status=status, detail=detail, items=created + per_issue_errors)
