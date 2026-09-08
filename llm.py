"""Thin wrapper around the Anthropic SDK shared by all agents."""
import json
import re

from anthropic import Anthropic

from config import Config

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        if not Config.anthropic_configured():
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. All agents require it (see Phase 0)."
            )
        _client = Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    return _client


def call_claude(system: str, user: str, max_tokens: int = 4096) -> str:
    client = get_client()
    response = client.messages.create(
        model=Config.ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def extract_json(text: str):
    """Pull a JSON array/object out of a Claude response that may be wrapped
    in prose or a ```json code fence."""
    fenced = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", text, re.DOTALL)
    candidate = fenced.group(1) if fenced else text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # Fall back to the widest [...] or {...} span in the text.
    for open_ch, close_ch in ("[", "]"), ("{", "}"):
        start = candidate.find(open_ch)
        end = candidate.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(candidate[start : end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Could not parse JSON from model output: {text[:500]}")
