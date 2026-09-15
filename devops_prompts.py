"""Prompt templates for the 7-agent DevOps pipeline's LLM stages
(Classifier, Severity, Root Cause, Remediation, Cookbook).
"""
from langchain_core.prompts import ChatPromptTemplate

classifier_prompt = ChatPromptTemplate.from_template("""
You are an expert DevOps log analyzer.
Analyze the provided logs and generate a clear, structured incident analysis report.

Your analysis should include:
1. Executive Summary — what happened, likely root cause, and impact.
2. Issues Detected — severity, title, detail, affected component, timestamp, log snippet.
3. Affected Services — all impacted services, APIs, containers, databases, infrastructure.
4. Error Patterns & Observations — recurring failures, spikes, timeouts, cascading issues.
5. Timeline of Key Events — chronological incident timeline.
6. Root Cause Analysis — most probable root cause with correlated failures.
7. Recommended Remediation — actionable fixes and preventive recommendations.

Also identify the log type. Valid categories (pick the BEST match):
- kubernetes  : Pod crashes, kubelet, CrashLoopBackOff, Deployments, Nodes
- nginx       : Reverse proxy errors, 502/504, upstream failures, access/error logs
- cloudwatch  : AWS CloudWatch alarms, Lambda, RDS, ECS, EC2 metrics
- application : Python/Java/Node tracebacks, exceptions, stack traces, API errors
- database    : PostgreSQL/MySQL/Oracle errors, deadlocks, connection pools, replication
- mixed       : Logs spanning multiple infrastructure types in one file
- other       : Anything that does not clearly match the above categories

If unsure, classify as "other" and still provide the best possible analysis.
NEVER respond with "unknown" — always pick a category or use "other".

LOGS TO ANALYZE:
{log_content}
""")

severity_prompt = ChatPromptTemplate.from_template("""
You are a senior SRE responsible for incident severity triage.

Based on the incident analysis below, assign a severity level and extract critical issues.

Severity Scale:
- P1 (CRITICAL): Complete production outage, data loss risk, payment failure, revenue impact
- P2 (HIGH): Major service degradation, >20% error rate, auth outage, partial outage
- P3 (MEDIUM): Non-critical service impact, elevated errors, no direct customer impact
- P4 (LOW): Minor issues, warnings, cosmetic, informational

Respond in this EXACT format:
SEVERITY: P{{1/2/3/4}}
RATIONALE: <one sentence explaining why>
CRITICAL_ISSUES:
- <issue 1 title>: <one line description>
- <issue 2 title>: <one line description>
(list only P1/P2 level issues; write "None" if severity is P3 or P4)

INCIDENT ANALYSIS:
{log_summary}
""")

root_cause_prompt = ChatPromptTemplate.from_template("""
You are a senior SRE engineer performing root cause analysis.

Your RCA should include:
1. Primary Root Cause — the single most likely cause
2. Contributing Factors — what made it worse or harder to detect
3. Cascading Failures — how one failure triggered others
4. Blast Radius — services/users affected and severity
5. Timeline Correlation — key events in order
6. Similar Historical Incidents — patterns from the knowledge base

INCIDENT ANALYSIS:
{log_summary}

HISTORICAL KNOWLEDGE BASE CONTEXT:
{rag_context}

CRITICAL ISSUES IDENTIFIED:
{critical_issues}
""")

remediation_prompt = ChatPromptTemplate.from_template("""
You are an expert DevOps Site Reliability Engineer (SRE).

Analyze the detected issues and generate a detailed remediation report.

ISSUES FOUND:
{issues_text}

ROOT CAUSE ANALYSIS:
{root_cause}

Your response should include:
1. Overall Recommendation — system state, prioritization rationale.
2. Priority Order — issues ordered by severity and impact.
3. Detailed Remediation Plan — for each issue:
   - Issue ID, Severity, Title, Root Cause Analysis
   - Immediate Action (fastest mitigation)
   - Step-by-Step Resolution (numbered)
   - Recommended Commands (shell/kubectl/docker/SQL)
   - Prevention Measures
   - Estimated Resolution Time
""")

cookbook_prompt = ChatPromptTemplate.from_template("""
You are a senior DevOps engineer creating operational incident response runbooks.

ISSUES DETECTED:
{issues_text}

REMEDIATION STEPS:
{remediation_text}

Your runbook should include:
1. Runbook Title — concise and descriptive
2. Incident Type
3. Severity Level
4. Purpose — who this is for and what it addresses
5. Pre-Checks — health checks, resource utilization, alert validation
6. Incident Response Checklist:
   ### Detection Phase
   ### Containment Phase
   ### Resolution Phase
   ### Post-Incident Phase
7. Escalation Path — On-call → SRE → Infra Lead → EM → CTO
8. Key Metrics to Monitor
9. Prevention Measures
10. Lessons Learned
""")
