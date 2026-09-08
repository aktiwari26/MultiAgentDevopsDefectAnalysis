"""Remediation agent — generates a fix, rationale, and concrete steps per
issue found by the Log Reader agent."""
from llm import call_claude, extract_json
from state import Issue, Remediation

SYSTEM_PROMPT = """You are a senior SRE writing remediation guidance.

You will receive a JSON array of issues extracted from an ops log. For
EVERY issue (in the same order, one remediation each), produce:
  "issue_id": copy the issue's "id" field verbatim
  "fix": one-sentence summary of the recommended fix
  "rationale": why this fix addresses the root cause, not just the symptom
  "steps": an array of 2-6 short, concrete, actionable step strings an
           on-call engineer could follow directly

Respond with ONLY a JSON array (no prose, no markdown fence).
"""


class RemediationAgent:
    def run(self, issues: list[Issue]) -> list[Remediation]:
        if not issues:
            return []
        payload = [dict(issue) for issue in issues]
        raw = call_claude(SYSTEM_PROMPT, str(payload))
        parsed = extract_json(raw)

        by_id = {item.get("issue_id"): item for item in parsed if isinstance(item, dict)}
        remediations: list[Remediation] = []
        for issue in issues:
            item = by_id.get(issue["id"], {})
            remediations.append(
                Remediation(
                    issue_id=issue["id"],
                    fix=str(item.get("fix", "Manual investigation required.")),
                    rationale=str(item.get("rationale", "")),
                    steps=[str(s) for s in item.get("steps", [])],
                )
            )
        return remediations
