"""Jira Ticket agent — UC-3, with UC-6 degraded-mode semantics: each
ticket attempt is isolated, so one failure never blocks the rest of the
batch or the pipeline.

Defaults to JIRA_MOCK_MODE=True: no network calls are made, and fake
ticket keys are returned so the rest of the app (checklist, UI) is fully
exercisable without a real Jira instance. Set JIRA_MOCK_MODE=False (and
provide JIRA_SERVER/EMAIL/API_TOKEN/PROJECT_KEY) to file real tickets.
"""
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


def _resolve_sprint_id(auth: tuple[str, str]) -> int | None:
    """Best-effort: resolve JIRA_SPRINT_NAME to a numeric sprint id via the
    Agile API. Returns None (and sprint assignment is simply skipped) if
    the project has no board, the sprint isn't found, or the instance
    doesn't expose the Agile API to this account."""
    if not Config.JIRA_SPRINT_NAME:
        return None
    base = Config.JIRA_SERVER.rstrip("/")
    try:
        boards = requests.get(
            f"{base}/rest/agile/1.0/board",
            params={"projectKeyOrId": Config.JIRA_PROJECT_KEY},
            auth=auth,
            timeout=10,
        )
        if boards.status_code != 200:
            return None
        for board in boards.json().get("values", []):
            sprints = requests.get(
                f"{base}/rest/agile/1.0/board/{board['id']}/sprint",
                params={"state": "active,future"},
                auth=auth,
                timeout=10,
            )
            if sprints.status_code != 200:
                continue
            for sprint in sprints.json().get("values", []):
                if sprint.get("name") == Config.JIRA_SPRINT_NAME:
                    return sprint.get("id")
    except requests.RequestException:
        return None
    return None


class JiraAgent:
    def __init__(self, dedup_store: DedupStore | None = None):
        self.dedup_store = dedup_store or DedupStore(namespace="jira")

    def run(self, issues: list[Issue], remediations: list[Remediation]) -> IntegrationResult:
        if not Config.jira_active():
            return IntegrationResult(status="skipped", detail="Jira not configured and mock mode is off.")

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

        if Config.JIRA_MOCK_MODE:
            result = self._run_mock(fresh_issues, remediations)
        else:
            result = self._run_real(fresh_issues, remediations)

        succeeded_ids = {item["issue_id"] for item in result["items"] if "key" in item}
        if succeeded_ids:
            self.dedup_store.mark_all_seen([i for i in fresh_issues if i["id"] in succeeded_ids])

        if suppressed:
            result["detail"] += f" ({len(suppressed)} suppressed as duplicates.)"
        return result

    def _run_mock(self, issues: list[Issue], remediations: list[Remediation]) -> IntegrationResult:
        items = []
        for i, issue in enumerate(issues):
            key = f"{Config.JIRA_PROJECT_KEY or 'MOCK'}-{1000 + i}"
            item = {
                "issue_id": issue["id"],
                "key": key,
                "url": f"{Config.JIRA_SERVER.rstrip('/')}/browse/{key}" if Config.JIRA_SERVER else f"(mock) {key}",
                "mock": True,
            }
            if Config.JIRA_EPIC_KEY:
                item["epic"] = Config.JIRA_EPIC_KEY
            if Config.JIRA_SPRINT_NAME:
                item["sprint"] = Config.JIRA_SPRINT_NAME
            items.append(item)
        return IntegrationResult(status="sent", detail=f"[MOCK] Created {len(items)} ticket(s).", items=items)

    def _run_real(self, issues: list[Issue], remediations: list[Remediation]) -> IntegrationResult:
        remediation_by_id = {r["issue_id"]: r for r in remediations}
        url = f"{Config.JIRA_SERVER.rstrip('/')}/rest/api/3/issue"
        auth = (Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
        sprint_id = _resolve_sprint_id(auth) if Config.JIRA_SPRINT_NAME else None

        created, per_issue_errors = [], []
        for issue in issues:
            remediation = remediation_by_id.get(issue["id"])
            fields = {
                "project": {"key": Config.JIRA_PROJECT_KEY},
                "summary": f"[{issue['severity'].upper()}] {issue['category']} — {issue['service']}",
                "description": _build_description(issue, remediation),
                "issuetype": {"name": Config.JIRA_ISSUE_TYPE},
            }
            if Config.JIRA_EPIC_KEY:
                # "parent" is the team-managed (next-gen) convention; classic
                # (company-managed) projects use a custom Epic Link field
                # instead, whose id varies per instance.
                fields["parent"] = {"key": Config.JIRA_EPIC_KEY}
            if sprint_id is not None:
                fields[Config.JIRA_SPRINT_FIELD_ID] = sprint_id

            try:
                resp = requests.post(url, json={"fields": fields}, auth=auth, timeout=15)
                if resp.status_code in (200, 201):
                    key = resp.json().get("key")
                    created.append(
                        {
                            "issue_id": issue["id"],
                            "key": key,
                            "url": f"{Config.JIRA_SERVER.rstrip('/')}/browse/{key}",
                        }
                    )
                else:
                    per_issue_errors.append(
                        {"issue_id": issue["id"], "error": f"HTTP {resp.status_code}: {resp.text[:300]}"}
                    )
            except requests.RequestException as exc:
                per_issue_errors.append({"issue_id": issue["id"], "error": str(exc)})

        if created and not per_issue_errors:
            status = "sent"
        elif per_issue_errors:
            status = "error"
        else:
            status = "no_op"

        detail = f"Created {len(created)} ticket(s)"
        if per_issue_errors:
            detail += f", {len(per_issue_errors)} failed"
        detail += "."
        if Config.JIRA_SPRINT_NAME and sprint_id is None:
            detail += f" (Could not resolve sprint '{Config.JIRA_SPRINT_NAME}'; sprint assignment skipped.)"

        return IntegrationResult(status=status, detail=detail, items=created + per_issue_errors)
