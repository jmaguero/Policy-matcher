import json
import re

import httpx
from anthropic import Anthropic
from openai import OpenAI

from config import ANTHROPIC_API_KEY, OLLAMA_HOST, OPENAI_API_KEY

_anthropic: Anthropic | None = None
_openai: OpenAI | None = None


def _get_anthropic() -> Anthropic:
    global _anthropic
    if _anthropic is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        _anthropic = Anthropic(api_key=ANTHROPIC_API_KEY)
    return _anthropic


def _get_openai() -> OpenAI:
    global _openai
    if _openai is None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not set")
        _openai = OpenAI(api_key=OPENAI_API_KEY)
    return _openai


def _parse_json(text: str) -> dict:
    """Parse JSON, stripping markdown fences if needed."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            return json.loads(m.group(1))
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def _call_anthropic(model: str, system_prompt: str, user_prompt: str) -> str:
    msg = _get_anthropic().messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return msg.content[0].text


def _call_openai(model: str, system_prompt: str, user_prompt: str) -> str:
    resp = _get_openai().chat.completions.create(
        model=model,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content


def _call_ollama(model: str, system_prompt: str, user_prompt: str) -> str:
    if not OLLAMA_HOST:
        raise ValueError("OLLAMA_HOST is not configured")
    try:
        r = httpx.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            },
            timeout=60,
        )
        r.raise_for_status()
    except httpx.InvalidURL:
        raise ValueError(f"OLLAMA_HOST is not a valid URL: {OLLAMA_HOST!r}")
    except httpx.ConnectError:
        raise ValueError(f"Could not connect to Ollama at {OLLAMA_HOST}")
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Ollama returned HTTP {e.response.status_code}")
    return r.json()["message"]["content"]


def call_llm(
    provider: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    required_keys: list[str] | None = None,
) -> dict:
    if provider not in ("anthropic", "openai", "ollama"):
        raise ValueError(f"Unknown provider: {provider!r}")

    _dispatch = {
        "anthropic": _call_anthropic,
        "openai": _call_openai,
        "ollama": _call_ollama,
    }

    for _ in range(3):
        raw = _dispatch[provider](model, system_prompt, user_prompt)
        try:
            result = _parse_json(raw)
        except json.JSONDecodeError:
            continue
        if required_keys and not all(k in result for k in required_keys):
            continue
        return result

    raise RuntimeError("LLM failed to return valid JSON with required keys after 3 attempts")
