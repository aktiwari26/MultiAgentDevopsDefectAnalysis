"""Notification agent — UC-2 (Slack), with UC-6 degraded-mode semantics:
any failure here is caught and recorded, never raised, so the pipeline
always continues to Jira/Cookbook regardless of Slack outcome.
"""
from config import Config
from dedup import DedupStore
from state import Issue, Remediation, IntegrationResult

SEVERITY_EMOJI = {
    "critical": "\U0001F534",  # red circle
    "high": "\U0001F7E0",  # orange circle
    "medium": "\U0001F7E1",  # yellow circle
    "low": "\U0001F7E2",  # green circle
}

# Slack hard-caps a message at 50 blocks; stay comfortably under that so a
# large batch of issues doesn't get rejected outright (Phase 2 hardening).
MAX_ISSUES_PER_MESSAGE = 20


def _build_blocks(issues: list[Issue], remediation_by_id: dict[str, Remediation]) -> list[dict]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Incident Analysis: New Issues Detected"},
        }
    ]
    for issue in issues:
        emoji = SEVERITY_EMOJI.get(issue["severity"], "⚪")
        remediation = remediation_by_id.get(issue["id"])
        fix_line = f"*Fix:* {remediation['fix']}" if remediation else "_No remediation available._"
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"{emoji} *{issue['severity'].upper()}* — *{issue['category']}* "
                        f"on `{issue['service']}` (x{issue['count']})\n"
                        f"{issue['message']}\n{fix_line}"
                    ),
                },
            }
        )
        blocks.append({"type": "divider"})
    return blocks


class NotificationAgent:
    def __init__(self, dedup_store: DedupStore | None = None):
        self.dedup_store = dedup_store or DedupStore()

    def run(self, issues: list[Issue], remediations: list[Remediation]) -> IntegrationResult:
        if not Config.slack_configured():
            return IntegrationResult(status="skipped", detail="Slack token/channel not configured.")

        fresh_issues, suppressed = self.dedup_store.filter_new(issues)
        if not fresh_issues:
            return IntegrationResult(
                status="no_op",
                detail=f"All {len(suppressed)} issue(s) already notified within the dedup window.",
            )

        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
        except ImportError as exc:
            return IntegrationResult(status="error", detail=f"slack_sdk not installed: {exc}")

        client = WebClient(token=Config.SLACK_BOT_TOKEN)
        remediation_by_id = {r["issue_id"]: r for r in remediations}
        sent_timestamps = []

        try:
            for i in range(0, len(fresh_issues), MAX_ISSUES_PER_MESSAGE):
                chunk = fresh_issues[i : i + MAX_ISSUES_PER_MESSAGE]
                blocks = _build_blocks(chunk, remediation_by_id)
                response = client.chat_postMessage(
                    channel=Config.SLACK_CHANNEL,
                    blocks=blocks,
                    text=f"Incident analysis: {len(chunk)} issue(s) detected",
                )
                sent_timestamps.append(response["ts"])
            self.dedup_store.mark_all_seen(fresh_issues)
            detail = f"Posted {len(fresh_issues)} issue(s) to {Config.SLACK_CHANNEL}."
            if suppressed:
                detail += f" ({len(suppressed)} suppressed as duplicates.)"
            return IntegrationResult(
                status="sent",
                detail=detail,
                items=[{"ts": ts} for ts in sent_timestamps],
            )
        except SlackApiError as exc:
            return IntegrationResult(
                status="error",
                detail=f"Slack API error: {exc.response.get('error', str(exc))}",
            )
        except Exception as exc:  # noqa: BLE001 - must never bubble up (UC-6)
            return IntegrationResult(status="error", detail=f"Unexpected Slack error: {exc}")
