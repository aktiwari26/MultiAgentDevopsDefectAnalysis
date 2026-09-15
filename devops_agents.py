"""The 7 LangGraph node functions for the DevOps pipeline: Classifier,
Severity, Root Cause (RAG-grounded), Remediation, Cookbook, Jira,
Notification.

Adapted from the reference React dashboard's backend pipeline:
  - build LLMs via langchain_openai.ChatOpenAI pointed at OpenRouter
    (configured by the caller; see api/main.py), instead of a dedicated
    ChatOpenRouter/ChatOllama wrapper class.
  - default Jira/Notification credentials from this project's Config
    (config.py) rather than only accepting them as call arguments.
  - reuse this project's already-TLS-fixed `requests` (see config.py's
    truststore.inject_into_ssl() call) instead of introducing separate
    TLS handling.
  - plain-ASCII log lines instead of emoji (Windows console codepages can
    raise UnicodeEncodeError on emoji, which would otherwise escape these
    nodes' own try/except and break the "no node ever raises" contract).

Every node follows the reference's non-fatal-error convention: on any
exception, it writes a degraded-but-valid fallback value, appends to
`errors`, marks `pipeline_status[node] = {"status": "error", ...}`, and
returns normally — it never raises and never aborts the graph.
"""
from __future__ import annotations

import time
import random
from datetime import datetime
from typing import Any, Optional

import requests  # module-level import so tests can patch "devops_agents.requests"
from langchain_core.output_parsers import StrOutputParser

from config import Config
from devops_state import DevOpsState
from devops_parsers import (
    detect_log_type,
    parse_severity_response,
    severity_requires_approval,
    build_slack_blocks,
)
from devops_rag import search_knowledge_base

_llm_fast: Optional[Any] = None
_llm_reasoning: Optional[Any] = None
_llm_generation: Optional[Any] = None


def configure_llms(fast: Any, reasoning: Any, generation: Any) -> None:
    global _llm_fast, _llm_reasoning, _llm_generation
    _llm_fast = fast
    _llm_reasoning = reasoning
    _llm_generation = generation


def _elapsed(start: float) -> float:
    return round(time.time() - start, 2)


def _get_prompts():
    from devops_prompts import (
        classifier_prompt,
        severity_prompt,
        root_cause_prompt,
        remediation_prompt,
        cookbook_prompt,
    )
    return classifier_prompt, severity_prompt, root_cause_prompt, remediation_prompt, cookbook_prompt


# ── Agent 1: Classifier ──────────────────────────────────────────────────

def classifier_node(state: DevOpsState, llm: Optional[Any] = None) -> dict:
    print("[1/7] Classifier Agent - parsing and analyzing logs...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_fast

    try:
        cp, *_ = _get_prompts()
        chain = cp | llm | StrOutputParser()
        result = chain.invoke({"log_content": state["raw_logs"]})
        log_type = detect_log_type(state["raw_logs"])

        elapsed = _elapsed(start)
        status["classifier"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   done in {elapsed}s - detected log type: {log_type}")
        return {"log_summary": result, "log_type": log_type, "pipeline_status": status}

    except Exception as e:
        elapsed = _elapsed(start)
        status["classifier"] = {"status": "error", "elapsed_s": elapsed, "error": str(e)}
        print(f"   classifier error: {e}")
        return {
            "log_summary": f"Log analysis completed with partial results. The system will proceed with best-effort analysis.\n\nNote: {e}",
            "log_type": "other",
            "errors": [f"classifier: {e}"],
            "pipeline_status": status,
        }


# ── Agent 2: Severity ─────────────────────────────────────────────────────

def severity_node(state: DevOpsState, llm: Optional[Any] = None) -> dict:
    print("[2/7] Severity Agent - assigning P1-P4 severity...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_fast

    try:
        _, sp, *_ = _get_prompts()
        chain = sp | llm | StrOutputParser()
        result_text = chain.invoke({"log_summary": state["log_summary"]})

        parsed = parse_severity_response(result_text)
        approval_required, approval_status = severity_requires_approval(parsed["severity"])

        elapsed = _elapsed(start)
        status["severity"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   done in {elapsed}s - severity: {parsed['severity']} | issues: {len(parsed['critical_issues'])}")
        return {
            "severity": parsed["severity"],
            "severity_rationale": parsed["rationale"],
            "critical_issues": parsed["critical_issues"],
            "approval_required": approval_required,
            "approval_status": approval_status,
            "pipeline_status": status,
        }

    except Exception as e:
        elapsed = _elapsed(start)
        status["severity"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   severity error: {e}")
        return {
            "severity": "P2",
            "severity_rationale": f"Default P2 assigned due to error: {e}",
            "critical_issues": [],
            "approval_required": True,
            "approval_status": "auto_approved",
            "errors": [f"severity: {e}"],
            "pipeline_status": status,
        }


# ── Agent 3: Root Cause (RAG-grounded) ───────────────────────────────────

def root_cause_node(
    state: DevOpsState,
    llm: Optional[Any] = None,
    query_engine: Optional[Any] = None,
) -> dict:
    print("[3/7] Root Cause Agent - querying knowledge base then analyzing...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_reasoning

    log_type = state.get("log_type", "incident")
    issues = state.get("critical_issues") or []
    issue_titles = " ".join([
        i.get("title", i) if isinstance(i, dict) else str(i)
        for i in issues[:3]
    ])
    rag_query = f"{log_type} {issue_titles} {state['log_summary'][:200]}"

    # Retrieval happens unconditionally, before the try/except, so RAG
    # context is captured even if the subsequent LLM call fails.
    print(f"   RAG query: {rag_query[:80]}...")
    rag_result = search_knowledge_base(rag_query, query_engine=query_engine)
    print(f"   retrieved {len(rag_result)} chars from knowledge base")

    try:
        _, _, rca_p, *_ = _get_prompts()
        chain = rca_p | llm | StrOutputParser()

        issues_text = "\n".join([
            f"- {i.get('title', i) if isinstance(i, dict) else i}"
            for i in issues
        ]) or "No specific critical issues extracted."

        result = chain.invoke({
            "log_summary": state["log_summary"],
            "rag_context": rag_result,
            "critical_issues": issues_text,
        })

        elapsed = _elapsed(start)
        status["root_cause"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   done in {elapsed}s")
        return {
            "root_cause_analysis": result,
            "rag_context": [rag_result],
            "pipeline_status": status,
        }

    except Exception as e:
        elapsed = _elapsed(start)
        status["root_cause"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   RCA error: {e}")
        return {
            "root_cause_analysis": f"RCA unavailable: {e}",
            "rag_context": [rag_result],
            "errors": [f"root_cause: {e}"],
            "pipeline_status": status,
        }


# ── Agent 4: Remediation ──────────────────────────────────────────────────

def remediation_node(state: DevOpsState, llm: Optional[Any] = None) -> dict:
    print("[4/7] Remediation Agent - generating fix plan...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_reasoning

    try:
        _, _, _, rem_p, _ = _get_prompts()
        chain = rem_p | llm | StrOutputParser()
        result = chain.invoke({
            "issues_text": state["log_summary"],
            "root_cause": state.get("root_cause_analysis") or "RCA not available",
        })

        elapsed = _elapsed(start)
        status["remediation"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   done in {elapsed}s")
        return {"remediation_plan": result, "pipeline_status": status}

    except Exception as e:
        elapsed = _elapsed(start)
        status["remediation"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   remediation error: {e}")
        return {
            "remediation_plan": f"Remediation plan unavailable: {e}",
            "errors": [f"remediation: {e}"],
            "pipeline_status": status,
        }


# ── Agent 5: Cookbook ─────────────────────────────────────────────────────

def cookbook_node(state: DevOpsState, llm: Optional[Any] = None) -> dict:
    print("[5/7] Cookbook Agent - synthesizing operational runbook...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    llm = llm or _llm_generation

    try:
        _, _, _, _, cb_p = _get_prompts()
        chain = cb_p | llm | StrOutputParser()
        result = chain.invoke({
            "issues_text": state["log_summary"],
            "remediation_text": state.get("remediation_plan") or "See log analysis above.",
        })

        elapsed = _elapsed(start)
        status["cookbook"] = {"status": "done", "elapsed_s": elapsed}
        print(f"   done in {elapsed}s")
        return {"cookbook": result, "pipeline_status": status}

    except Exception as e:
        elapsed = _elapsed(start)
        status["cookbook"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   cookbook error: {e}")
        return {
            "cookbook": f"Cookbook generation failed: {e}",
            "errors": [f"cookbook: {e}"],
            "pipeline_status": status,
        }


# ── Agent 6: Jira ──────────────────────────────────────────────────────────

def jira_node(
    state: DevOpsState,
    mock_mode: bool = None,
    jira_server: str = None,
    jira_email: str = None,
    jira_api_token: str = None,
    jira_project_key: str = None,
    jira_epic_key: str = None,
    jira_sprint_name: str = None,
) -> dict:
    """Files one incident-level ticket for P1/P2 severities (and always for
    the 'other' log type, at P4/Low). Skips silently for P3/P4 on known log
    types. Defaults every credential from Config when not passed explicitly."""
    mock_mode = Config.JIRA_MOCK_MODE if mock_mode is None else mock_mode
    jira_server = Config.JIRA_SERVER if jira_server is None else jira_server
    jira_email = Config.JIRA_EMAIL if jira_email is None else jira_email
    jira_api_token = Config.JIRA_API_TOKEN if jira_api_token is None else jira_api_token
    jira_project_key = (Config.JIRA_PROJECT_KEY or "OPS") if jira_project_key is None else jira_project_key
    jira_epic_key = Config.JIRA_EPIC_KEY if jira_epic_key is None else jira_epic_key
    jira_sprint_name = Config.JIRA_SPRINT_NAME if jira_sprint_name is None else jira_sprint_name

    print("[6/7] JIRA Agent - creating incident tickets...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    severity = state.get("severity", "P2")
    log_type = state.get("log_type", "other")

    is_other = log_type == "other"
    if severity in ("P3", "P4") and not is_other:
        print(f"   skipped - {severity} does not require a JIRA ticket")
        status["jira"] = {"status": "skipped", "reason": "severity < P2"}
        return {"jira_tickets": [], "pipeline_status": status}
    effective_severity = "P4" if is_other and severity not in ("P1", "P2") else severity

    try:
        if mock_mode:
            ticket_num = random.randint(100, 999)
            eff_sev = effective_severity
            tickets = [{
                "key": f"{jira_project_key}-{ticket_num}",
                "url": f"{jira_server.rstrip('/')}/browse/{jira_project_key}-{ticket_num}" if jira_server else f"(mock) {jira_project_key}-{ticket_num}",
                "summary": f"[{eff_sev}] AI Detected Incident — {log_type.upper()}",
                "status": "Open",
                "mode": "mock",
                "epic": jira_epic_key or "(none)",
                "sprint": jira_sprint_name or "(none)",
            }]
            print(f"   MOCK: ticket {tickets[0]['key']} created")
        else:
            priority_map = {"P1": "Highest", "P2": "High", "P3": "Medium", "P4": "Low"}
            eff_sev = effective_severity
            rca = state.get("root_cause_analysis", "") or ""
            remed = state.get("remediation_plan", "") or ""
            adf_body = {
                "type": "doc", "version": 1,
                "content": [
                    {"type": "heading", "attrs": {"level": 2},
                     "content": [{"type": "text", "text": f"[DevOps] {severity} Incident Auto-Analysis"}]},
                    {"type": "heading", "attrs": {"level": 3},
                     "content": [{"type": "text", "text": "Root Cause Analysis"}]},
                    {"type": "paragraph",
                     "content": [{"type": "text", "text": rca[:2000] if rca else "See log summary."}]},
                    {"type": "heading", "attrs": {"level": 3},
                     "content": [{"type": "text", "text": "Remediation Plan"}]},
                    {"type": "paragraph",
                     "content": [{"type": "text", "text": remed[:2000] if remed else "See recommendations."}]},
                    {"type": "paragraph",
                     "content": [{"type": "text", "text": "Generated by DevOps Multi-Agent Pipeline.", "marks": [{"type": "em"}]}]},
                ]
            }

            sprint_id = None
            base = jira_server.rstrip("/")
            if jira_sprint_name and jira_project_key:
                try:
                    boards_resp = requests.get(
                        f"{base}/rest/agile/1.0/board",
                        auth=(jira_email, jira_api_token),
                        params={"projectKeyOrId": jira_project_key, "type": "scrum"},
                        timeout=10,
                    )
                    boards_resp.raise_for_status()
                    for board in boards_resp.json().get("values", []):
                        sprints_resp = requests.get(
                            f"{base}/rest/agile/1.0/board/{board['id']}/sprint",
                            auth=(jira_email, jira_api_token),
                            params={"state": "active,future"},
                            timeout=10,
                        )
                        if sprints_resp.ok:
                            for sp in sprints_resp.json().get("values", []):
                                if sp.get("name", "").strip() == jira_sprint_name.strip():
                                    sprint_id = sp["id"]
                                    break
                        if sprint_id:
                            break
                    if sprint_id:
                        print(f"   sprint resolved: '{jira_sprint_name}' -> ID {sprint_id}")
                    else:
                        print(f"   sprint '{jira_sprint_name}' not found - ticket created without sprint")
                except Exception as sp_err:
                    print(f"   sprint lookup failed ({sp_err}) - continuing without sprint")

            fields_payload = {
                "project": {"key": jira_project_key},
                "summary": f"[{eff_sev}] AI Incident: {log_type.upper()} — DevOps",
                "issuetype": {"name": Config.JIRA_ISSUE_TYPE or "Task"},
                "priority": {"name": priority_map.get(eff_sev, "Low")},
                "description": adf_body,
            }
            if jira_epic_key:
                try:
                    epic_fields_resp = requests.get(
                        f"{base}/rest/api/3/field",
                        auth=(jira_email, jira_api_token),
                        timeout=10,
                    )
                    epic_fields_resp.raise_for_status()
                    epic_field_key = None
                    for field in epic_fields_resp.json():
                        if field.get("name", "").strip().lower() == "epic link":
                            epic_field_key = field["id"]
                            break
                    if epic_field_key:
                        fields_payload[epic_field_key] = jira_epic_key
                        print(f"   epic -> {jira_epic_key} ({epic_field_key})")
                    else:
                        fields_payload["parent"] = {"key": jira_epic_key}
                        print(f"   epic link field not found - using 'parent' -> {jira_epic_key}")
                except Exception as epic_err:
                    print(f"   epic field lookup failed ({epic_err}) - skipping epic assignment")

            if sprint_id:
                fields_payload[Config.JIRA_SPRINT_FIELD_ID or "customfield_10020"] = [sprint_id]
                print(f"   sprint -> {jira_sprint_name} (ID {sprint_id})")

            resp = requests.post(
                f"{base}/rest/api/3/issue",
                auth=(jira_email, jira_api_token),
                json={"fields": fields_payload},
                timeout=15,
            )
            resp.raise_for_status()
            issue_data = resp.json()
            issue_key = issue_data["key"]
            tickets = [{
                "key": issue_key,
                "url": f"{base}/browse/{issue_key}",
                "summary": f"[{eff_sev}] AI Incident",
                "status": "Open",
                "mode": "live",
                "epic": jira_epic_key or None,
                "sprint": jira_sprint_name or None,
            }]
            print(f"   LIVE: ticket {issue_key} created -> {base}/browse/{issue_key}")

        elapsed = _elapsed(start)
        status["jira"] = {"status": "done", "elapsed_s": elapsed}
        return {"jira_tickets": tickets, "pipeline_status": status}

    except Exception as e:
        elapsed = _elapsed(start)
        status["jira"] = {"status": "error", "elapsed_s": elapsed}
        print(f"   JIRA error (non-fatal): {e}")
        return {
            "jira_tickets": [{"key": "ERR", "error": str(e), "mode": "failed"}],
            "errors": [f"jira: {e}"],
            "pipeline_status": status,
        }


# ── Agent 7: Notification ─────────────────────────────────────────────────

def notification_node(
    state: DevOpsState,
    mock_mode: bool = None,
    n8n_webhook_url: str = None,
    slack_webhook_url: str = None,
    http_timeout: int = 8,
) -> dict:
    mock_mode = Config.NOTIFICATION_MOCK_MODE if mock_mode is None else mock_mode
    n8n_webhook_url = Config.N8N_WEBHOOK_URL if n8n_webhook_url is None else n8n_webhook_url
    slack_webhook_url = Config.SLACK_WEBHOOK_URL if slack_webhook_url is None else slack_webhook_url

    print("[7/7] Notification Agent - sending alerts...")
    start = time.time()
    status = dict(state.get("pipeline_status") or {})
    receipts = []

    if mock_mode:
        print("   MOCK: n8n + Slack notifications sent")
        receipts = [
            {"channel": "n8n", "status": "delivered_mock", "timestamp": datetime.utcnow().isoformat()},
            {"channel": "slack", "status": "delivered_mock", "timestamp": datetime.utcnow().isoformat()},
        ]
        status["notification"] = {"status": "done_mock", "elapsed_s": _elapsed(start)}
        return {"notifications_sent": receipts, "pipeline_status": status}

    payload = {
        "event_type": "incident_detected",
        "severity": state.get("severity", "P2"),
        "log_type": state.get("log_type", "other"),
        "rationale": state.get("severity_rationale", ""),
        "critical_issues": [
            i.get("title", i) if isinstance(i, dict) else i
            for i in (state.get("critical_issues") or [])[:5]
        ],
        "jira_tickets": [t.get("key") for t in (state.get("jira_tickets") or [])],
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "source": "DevOps Multi-Agent Pipeline",
    }

    n8n_ok = False
    if n8n_webhook_url:
        try:
            resp = requests.post(n8n_webhook_url, json=payload, timeout=http_timeout)
            resp.raise_for_status()
            receipts.append({"channel": "n8n", "status": "delivered", "http_status": resp.status_code})
            n8n_ok = True
            print(f"   n8n delivered (HTTP {resp.status_code})")
        except Exception as e:
            print(f"   n8n failed ({e}) - falling back to Slack")

    if slack_webhook_url and not n8n_ok:
        try:
            blocks = build_slack_blocks(
                severity=state.get("severity", "P2"),
                log_type=state.get("log_type", "other"),
                severity_rationale=state.get("severity_rationale", ""),
                critical_issues=state.get("critical_issues") or [],
            )
            resp = requests.post(
                slack_webhook_url,
                json={"blocks": blocks, "text": f"DevOps Alert — {state.get('severity')}"},
                timeout=http_timeout,
            )
            resp.raise_for_status()
            receipts.append({"channel": "slack", "status": "delivered", "http_status": resp.status_code})
            print(f"   slack delivered (HTTP {resp.status_code})")
        except Exception as e:
            receipts.append({"channel": "slack", "status": "failed", "error": str(e)})
            print(f"   slack failed: {e}")

    if not receipts:
        receipts = [{"channel": "none", "status": "no_webhook_configured"}]

    status["notification"] = {"status": "done", "elapsed_s": _elapsed(start)}
    return {"notifications_sent": receipts, "pipeline_status": status}
