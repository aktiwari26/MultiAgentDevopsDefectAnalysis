"""Environment-driven configuration for the DevOps Incident Analysis Suite.

Covers Phase 0 credentials: Anthropic (required), Slack (optional),
Jira (optional). Missing optional groups degrade their branch of the
graph gracefully rather than blocking the whole run (see UC-2/UC-3/UC-6).
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "")

    JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "")
    JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "Bug")

    # Phase 3: which severities are ticket-worthy (default matches the spec:
    # critical + high). Comma-separated env override, e.g. "critical".
    JIRA_TICKET_SEVERITIES = {
        s.strip().lower()
        for s in os.getenv("JIRA_TICKET_SEVERITIES", "critical,high").split(",")
        if s.strip()
    }

    # Phase 4: dedup window, in hours, for suppressing repeat notify/ticket
    # of an issue signature already raised recently.
    DEDUP_WINDOW_HOURS = float(os.getenv("DEDUP_WINDOW_HOURS", "24"))
    DEDUP_STORE_PATH = os.getenv("DEDUP_STORE_PATH", ".dedup_store.json")

    @classmethod
    def anthropic_configured(cls) -> bool:
        return bool(cls.ANTHROPIC_API_KEY)

    @classmethod
    def slack_configured(cls) -> bool:
        return bool(cls.SLACK_BOT_TOKEN and cls.SLACK_CHANNEL)

    @classmethod
    def jira_configured(cls) -> bool:
        return bool(
            cls.JIRA_BASE_URL
            and cls.JIRA_EMAIL
            and cls.JIRA_API_TOKEN
            and cls.JIRA_PROJECT_KEY
        )
