"""Notification agent — UC-2, with UC-6 degraded-mode semantics: any
failure here is caught and recorded, never raised, so the pipeline always
continues to Jira/Cookbook regardless of notification outcome.

Two independent channels, each optional:
  - Slack, via an incoming webhook URL (no bot token/scopes needed).
  - n8n, via a generic webhook URL, for downstream automation.
When NOTIFICATION_MOCK_MODE is on (the default), neither channel is
actually called — the payload is built and reported as "sent (mock)" so
the pipeline is fully exercisable without real webhooks configured.
"""
import requests

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


def _build_slack_blocks(issues: list[Issue], remediation_by_id: dict[str, Remediation]) -> list[dict]:
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


def _send_slack(issues: list[Issue], remediation_by_id: dict[str, Remediation]) -> dict:
    if not Config.slack_webhook_configured():
        return {"status": "skipped", "detail": "SLACK_WEBHOOK_URL not configured."}
    try:
        for i in range(0, len(issues), MAX_ISSUES_PER_MESSAGE):
            chunk = issues[i : i + MAX_ISSUES_PER_MESSAGE]
            blocks = _build_slack_blocks(chunk, remediation_by_id)
            resp = requests.post(
                Config.SLACK_WEBHOOK_URL,
                json={"blocks": blocks, "text": f"Incident analysis: {len(chunk)} issue(s) detected"},
                timeout=15,
            )
            if resp.status_code >= 300:
                return {"status": "error", "detail": f"Slack webhook HTTP {resp.status_code}: {resp.text[:300]}"}
        return {"status": "sent", "detail": f"Posted {len(issues)} issue(s) via Slack webhook."}
    except requests.RequestException as exc:
        return {"status": "error", "detail": f"Slack webhook error: {exc}"}


def _send_n8n(issues: list[Issue], remediation_by_id: dict[str, Remediation]) -> dict:
    if not Config.n8n_webhook_configured():
        return {"status": "skipped", "detail": "N8N_WEBHOOK_URL not configured."}
    try:
        payload = {
            "issues": [dict(issue) for issue in issues],
            "remediations": [
                dict(remediation_by_id[i["id"]]) for i in issues if i["id"] in remediation_by_id
            ],
        }
        resp = requests.post(Config.N8N_WEBHOOK_URL, json=payload, timeout=15)
        if resp.status_code >= 300:
            return {"status": "error", "detail": f"n8n webhook HTTP {resp.status_code}: {resp.text[:300]}"}
        return {"status": "sent", "detail": f"Posted {len(issues)} issue(s) to n8n."}
    except requests.RequestException as exc:
        return {"status": "error", "detail": f"n8n webhook error: {exc}"}


def _mock_channel_result(channel_configured: bool, label: str, count: int) -> dict:
    if channel_configured:
        return {"status": "sent", "detail": f"[MOCK] Would post {count} issue(s) via {label} (mock mode, not sent)."}
    return {"status": "skipped", "detail": f"{label} not configured (and mock mode is on)."}


class NotificationAgent:
    def __init__(self, dedup_store: DedupStore | None = None):
        self.dedup_store = dedup_store or DedupStore(namespace="notification")

    def run(self, issues: list[Issue], remediations: list[Remediation]) -> IntegrationResult:
        if not Config.notification_active():
            return IntegrationResult(
                status="skipped",
                detail="Notifications disabled: no webhook configured and mock mode is off.",
            )

        fresh_issues, suppressed = self.dedup_store.filter_new(issues)
        if not fresh_issues:
            return IntegrationResult(
                status="no_op",
                detail=f"All {len(suppressed)} issue(s) already notified within the dedup window.",
            )

        remediation_by_id = {r["issue_id"]: r for r in remediations}

        if Config.NOTIFICATION_MOCK_MODE:
            channels = {
                "slack": _mock_channel_result(Config.slack_webhook_configured(), "Slack", len(fresh_issues)),
                "n8n": _mock_channel_result(Config.n8n_webhook_configured(), "n8n", len(fresh_issues)),
            }
        else:
            channels = {
                "slack": _send_slack(fresh_issues, remediation_by_id),
                "n8n": _send_n8n(fresh_issues, remediation_by_id),
            }

        statuses = {c["status"] for c in channels.values()}
        if "sent" in statuses:
            # At least one channel got the message; suppress re-sending
            # this signature elsewhere within the window. A channel that
            # failed can still be retried on the next run since its issue
            # wasn't durably delivered anywhere.
            self.dedup_store.mark_all_seen(fresh_issues)

        if "error" in statuses:
            overall = "error"
        elif "sent" in statuses:
            overall = "sent"
        else:
            overall = "skipped"

        detail = f"Notified {len(fresh_issues)} issue(s)."
        if suppressed:
            detail += f" ({len(suppressed)} suppressed as duplicates.)"

        return IntegrationResult(status=overall, detail=detail, channels=channels)
