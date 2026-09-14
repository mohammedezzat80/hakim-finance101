"""LLM layer with a provider switch: LOCAL (Ollama) ⇄ ONLINE (Gemini).

The model is used for TWO narrow jobs only:
  1. Phrasing already-computed facts into a natural answer.
  2. Disambiguating a transaction the rules engine couldn't classify.
It NEVER computes totals, balances, or moves money. Every number the user sees
is computed in Python from Firefly data and passed to the model as fixed facts.

Privacy note (doctrine: local-first): in ONLINE mode only the question and the
FACTS JSON for that one answer leave the machine — never the ledger, never
account numbers. Local mode sends nothing anywhere.

Provider is chosen by, in order:  runtime toggle (POST /v1/provider or the
/switch page)  →  AGENT_PROVIDER env  →  "local". Falls back to templated text
if the chosen provider is unreachable.
"""
from __future__ import annotations

import json
import os
import httpx

from .config import config

_STATE_PATH = os.environ.get("AGENT_PROVIDER_STATE", "/tmp/hakim-agent-provider.json")
PROVIDERS = ("local", "online")


def get_provider() -> str:
    try:
        with open(_STATE_PATH) as fh:
            p = json.load(fh).get("provider")
            if p in PROVIDERS:
                return p
    except Exception:
        pass
    return config.PROVIDER if config.PROVIDER in PROVIDERS else "local"


def set_provider(p: str) -> str:
    if p not in PROVIDERS:
        raise ValueError(f"provider must be one of {PROVIDERS}")
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w") as fh:
        json.dump({"provider": p}, fh)
    return p


def _system() -> str:
    return (
        "You are HAKIM Finance, a careful read-only finance assistant. "
        "You are given a user question and a JSON object of FACTS that were "
        "computed from the user's ledger. Answer the question in 1-4 short "
        "sentences using ONLY the numbers in FACTS. Never invent figures. "
        f"All amounts are in {config.CURRENCY}. Reply in the language of the "
        "question (Arabic or English). Be direct and friendly."
    )


async def _ollama(question: str, facts: dict) -> str | None:
    async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT) as client:
        r = await client.post(f"{config.OLLAMA_URL}/api/chat", json={
            "model": config.MODEL, "stream": False,
            "options": {"temperature": 0.2},
            "messages": [{"role": "system", "content": _system()},
                         {"role": "user", "content": f"QUESTION: {question}\n\nFACTS (authoritative, do not alter numbers):\n{facts}"}],
        })
        r.raise_for_status()
        return r.json().get("message", {}).get("content", "").strip() or None


async def _gemini(question: str, facts: dict) -> str | None:
    if not config.GEMINI_API_KEY:
        return None
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{config.GEMINI_MODEL}:generateContent")
    async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT) as client:
        r = await client.post(url, params={"key": config.GEMINI_API_KEY}, json={
            "systemInstruction": {"parts": [{"text": _system()}]},
            "contents": [{"role": "user", "parts": [{"text":
                f"QUESTION: {question}\n\nFACTS (authoritative, do not alter numbers):\n{json.dumps(facts, ensure_ascii=False)}"}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 400},
        })
        r.raise_for_status()
        cands = r.json().get("candidates") or []
        parts = (cands[0].get("content", {}).get("parts") if cands else None) or []
        return "".join(p.get("text", "") for p in parts).strip() or None


async def phrase(question: str, facts: dict) -> str | None:
    """Ask the active provider to phrase `facts`. None on failure ⇒ templated text."""
    if not config.USE_LLM:
        return None
    try:
        if get_provider() == "online":
            return await _gemini(question, facts)
        return await _ollama(question, facts)
    except Exception:
        return None


async def available() -> dict:
    """Reachability of both providers, for the /switch page and health."""
    out = {"provider": get_provider(), "local": False, "online": bool(config.GEMINI_API_KEY),
           "local_model": config.MODEL, "online_model": config.GEMINI_MODEL}
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{config.OLLAMA_URL}/api/tags")
            out["local"] = r.status_code == 200
    except Exception:
        pass
    return out
