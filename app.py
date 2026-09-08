"""Streamlit entry point — UC-1: On-Demand Incident Analysis from an
Uploaded Log."""
import datetime as dt

import streamlit as st

from config import Config
from graph import run_pipeline

st.set_page_config(page_title="DevOps Incident Analysis Suite", layout="wide")

SEVERITY_BADGE = {
    "critical": "🔴 CRITICAL",
    "high": "🟠 HIGH",
    "medium": "🟡 MEDIUM",
    "low": "🟢 LOW",
}


def render_credential_banner():
    with st.expander("Environment status", expanded=not Config.anthropic_configured()):
        col1, col2, col3 = st.columns(3)
        col1.metric("Anthropic API", "Configured" if Config.anthropic_configured() else "Missing")
        col2.metric("Slack", "Configured" if Config.slack_configured() else "Not configured")
        col3.metric("Jira", "Configured" if Config.jira_configured() else "Not configured")
        if not Config.anthropic_configured():
            st.error("ANTHROPIC_API_KEY is required. Set it in .env before running an analysis.")


def render_issues_tab(issues, remediations):
    if not issues:
        st.success("No actionable issues detected. Log is clean.")
        return
    remediation_by_id = {r["issue_id"]: r for r in remediations}
    for issue in issues:
        badge = SEVERITY_BADGE.get(issue["severity"], issue["severity"])
        with st.container(border=True):
            st.markdown(f"**{badge} — {issue['category']}** on `{issue['service']}` (x{issue['count']})")
            st.write(issue["message"])
            remediation = remediation_by_id.get(issue["id"])
            if remediation:
                st.markdown(f"**Fix:** {remediation['fix']}")
                st.caption(remediation["rationale"])
                for step in remediation["steps"]:
                    st.checkbox(step, key=f"{issue['id']}-{step}", disabled=True)


def render_integration_status(name: str, result: dict | None):
    if result is None:
        st.info(f"{name}: not run.")
        return
    status = result.get("status")
    detail = result.get("detail", "")
    if status == "sent":
        st.success(f"{name}: {detail} ({dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    elif status in ("skipped", "no_op"):
        st.info(f"{name}: {detail}")
    else:
        st.error(f"{name}: {detail}")

    for item in result.get("items", []):
        if "key" in item:
            st.markdown(f"- [{item['key']}]({item['url']})")
        elif "error" in item:
            st.warning(f"- {item['issue_id']}: {item['error']}")


def main():
    st.title("Multi-Agent DevOps Incident Analysis Suite")
    render_credential_banner()

    uploaded = st.file_uploader("Upload a log file", type=["log", "txt", "json"])
    run_clicked = st.button("Run Multi-Agent Analysis", type="primary", disabled=uploaded is None)

    if run_clicked and uploaded is not None:
        log_content = uploaded.read().decode("utf-8", errors="replace")
        with st.spinner("Running Log Reader -> Remediation -> Notification -> Jira -> Cookbook..."):
            result = run_pipeline(log_content)
        st.session_state["result"] = result

    result = st.session_state.get("result")
    if not result:
        st.caption("Upload a log and click Run Multi-Agent Analysis to begin.")
        return

    for error in result.get("errors", []):
        st.error(error)

    issues_tab, checklist_tab, integrations_tab = st.tabs(
        ["Issues & Remediation", "Checklist", "Slack / Jira"]
    )

    with issues_tab:
        render_issues_tab(result.get("issues", []), result.get("remediations", []))

    with checklist_tab:
        checklist = result.get("checklist_md", "")
        st.markdown(checklist)
        st.download_button(
            "Download incident_checklist.md",
            data=checklist,
            file_name="incident_checklist.md",
            mime="text/markdown",
        )

    with integrations_tab:
        render_integration_status("Slack", result.get("slack_result"))
        render_integration_status("Jira", result.get("jira_result"))


if __name__ == "__main__":
    main()
