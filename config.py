"""Environment-driven configuration for the DevOps Incident Analysis Suite.

Covers credentials: OpenRouter (required), LangSmith (optional
observability), Jira (optional, mock by default), Slack/n8n notifications
(optional, mock by default). Missing optional groups degrade their branch
of the pipeline gracefully rather than blocking the whole run.
"""
import os

import truststore

# Corporate networks often TLS-intercept outbound HTTPS with a proxy CA that
# only the OS trust store knows about (not the certifi bundle requests/httpx
# ship with by default). Route all ssl.SSLContext creation through the OS
# store so `requests` (Slack/Jira/n8n) verifies the same way the `openai`
# SDK's bundled transport already does. Safe to call once, globally.
truststore.inject_into_ssl()

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: str = "True") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    # ── OpenRouter (LLM provider) ────────────────────────────────────────
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    # "fast/gen" tier — used for extraction/classification (Log Reader).
    MODEL_FAST = os.getenv("MODEL_FAST", "openai/gpt-4o-mini")
    # "reasoning" tier — used for generation that needs more reasoning
    # (Remediation).
    MODEL_REASONING = os.getenv("MODEL_REASONING", "openai/gpt-4o")
    # "generation" tier — used by the DevOps pipeline's Cookbook stage
    # (api/main.py, devops_agents.py). Defaults to the fast tier's model.
    MODEL_GENERATION = os.getenv("MODEL_GENERATION", "openai/gpt-4o-mini")

    # ── LangSmith (observability) ────────────────────────────────────────
    # Read directly by the langsmith/langchain-core SDKs from the process
    # environment (load_dotenv() above already populates os.environ), so no
    # extra plumbing is needed beyond having these set. Mirrored here only
    # so the UI can report whether tracing is active.
    LANGCHAIN_TRACING_V2 = _bool_env("LANGCHAIN_TRACING_V2", "False")
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "DevOps-Hackathon")
    LANGCHAIN_ENDPOINT = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")

    # ── Jira integration ─────────────────────────────────────────────────
    JIRA_MOCK_MODE = _bool_env("JIRA_MOCK_MODE", "True")
    JIRA_SERVER = os.getenv("JIRA_SERVER", "")
    JIRA_EMAIL = os.getenv("JIRA_EMAIL", "")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "")
    JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "")
    JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "Bug")
    JIRA_EPIC_KEY = os.getenv("JIRA_EPIC_KEY", "")
    JIRA_SPRINT_NAME = os.getenv("JIRA_SPRINT_NAME", "")
    # Sprint has no stable field id across Jira sites; customfield_10020 is
    # the common default on modern Jira Cloud instances but is overridable.
    JIRA_SPRINT_FIELD_ID = os.getenv("JIRA_SPRINT_FIELD_ID", "customfield_10020")

    # ── Slack / n8n notifications ────────────────────────────────────────
    NOTIFICATION_MOCK_MODE = _bool_env("NOTIFICATION_MOCK_MODE", "True")
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
    N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")

    @classmethod
    def openrouter_configured(cls) -> bool:
        return bool(cls.OPENROUTER_API_KEY)

    @classmethod
    def langsmith_configured(cls) -> bool:
        return cls.LANGCHAIN_TRACING_V2 and bool(cls.LANGCHAIN_API_KEY)

    @classmethod
    def jira_configured(cls) -> bool:
        """Whether *real* Jira ticket creation is usable (mock mode aside)."""
        return bool(
            cls.JIRA_SERVER
            and cls.JIRA_EMAIL
            and cls.JIRA_API_TOKEN
            and cls.JIRA_PROJECT_KEY
        )

    @classmethod
    def slack_webhook_configured(cls) -> bool:
        return bool(cls.SLACK_WEBHOOK_URL)

    @classmethod
    def n8n_webhook_configured(cls) -> bool:
        return bool(cls.N8N_WEBHOOK_URL)
