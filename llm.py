"""Thin LLM wrapper shared by all agents.

Talks to OpenRouter (an OpenAI-compatible endpoint) via the `openai` SDK.
When LangSmith tracing is enabled (LANGCHAIN_TRACING_V2=true +
LANGCHAIN_API_KEY set), the client is wrapped with
`langsmith.wrappers.wrap_openai` so every call shows up as a trace in the
configured LANGCHAIN_PROJECT without any per-call code changes elsewhere.
"""
import json
import re

from openai import OpenAI

from config import Config

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not Config.openrouter_configured():
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. All agents require it (see Phase 0)."
            )
        client = OpenAI(api_key=Config.OPENROUTER_API_KEY, base_url=Config.OPENROUTER_BASE_URL)
        if Config.langsmith_configured():
            from langsmith.wrappers import wrap_openai

            client = wrap_openai(client)
        _client = client
    return _client


def call_llm(system: str, user: str, tier: str = "fast", max_tokens: int = 4096) -> str:
    """tier: "fast" (extraction/classification) or "reasoning" (generation
    that benefits from a stronger model)."""
    model = Config.MODEL_REASONING if tier == "reasoning" else Config.MODEL_FAST
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response.choices[0].message.content or ""


def extract_json(text: str):
    """Pull a JSON array/object out of a model response that may be
    wrapped in prose or a ```json code fence."""
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
