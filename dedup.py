"""Phase 4: suppress re-notifying/re-ticketing an issue signature that was
already raised within a recent time window.

Signature = hash(category + service + message-pattern), matching the
execution plan's definition. Backed by a small JSON file so it survives
across Streamlit re-runs on the same machine.
"""
import hashlib
import json
import os
import re
import time

from config import Config
from state import Issue


def issue_signature(issue: Issue) -> str:
    # Strip digits/timestamps/ids from the message so near-identical repeats
    # of the same underlying problem hash the same.
    normalized_message = re.sub(r"\d+", "#", issue.get("message", ""))
    raw = f"{issue.get('category', '')}|{issue.get('service', '')}|{normalized_message}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DedupStore:
    def __init__(self, path: str = Config.DEDUP_STORE_PATH, window_hours: float = Config.DEDUP_WINDOW_HOURS):
        self.path = path
        self.window_seconds = window_hours * 3600

    def _load(self) -> dict:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def seen_recently(self, signature: str) -> bool:
        data = self._load()
        last_seen = data.get(signature)
        if last_seen is None:
            return False
        return (time.time() - last_seen) < self.window_seconds

    def mark_seen(self, signature: str) -> None:
        data = self._load()
        data[signature] = time.time()
        self._save(data)

    def filter_new(self, issues: list[Issue]) -> tuple[list[Issue], list[Issue]]:
        """Returns (fresh_issues, suppressed_issues)."""
        fresh, suppressed = [], []
        for issue in issues:
            sig = issue_signature(issue)
            if self.seen_recently(sig):
                suppressed.append(issue)
            else:
                fresh.append(issue)
        return fresh, suppressed

    def mark_all_seen(self, issues: list[Issue]) -> None:
        for issue in issues:
            self.mark_seen(issue_signature(issue))
