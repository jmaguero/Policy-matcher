import json
from unittest.mock import patch

import pytest

import llm as llm_module
from llm import _parse_json, call_llm


# ---------------------------------------------------------------------------
# _parse_json
# ---------------------------------------------------------------------------

def test_parse_json_plain_object():
    assert _parse_json('{"key": "value"}') == {"key": "value"}


def test_parse_json_fenced_with_language_tag():
    text = '```json\n{"key": "value"}\n```'
    assert _parse_json(text) == {"key": "value"}


def test_parse_json_fenced_without_language_tag():
    text = '```\n{"key": "value"}\n```'
    assert _parse_json(text) == {"key": "value"}


def test_parse_json_invalid_raises():
    with pytest.raises(json.JSONDecodeError):
        _parse_json("this is not json at all")


# ---------------------------------------------------------------------------
# call_llm — provider allowlist
# ---------------------------------------------------------------------------

def test_call_llm_rejects_unknown_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        call_llm("grok", "model", "sys", "usr")


def test_call_llm_rejects_empty_provider():
    with pytest.raises(ValueError, match="Unknown provider"):
        call_llm("", "model", "sys", "usr")


# ---------------------------------------------------------------------------
# call_llm — happy path (all three providers)
# ---------------------------------------------------------------------------

VALID_RESPONSE = '{"match": "yes", "if_yes_reason": "ok", "suggestions": ""}'
REQUIRED_KEYS = ["match", "if_yes_reason", "suggestions"]


@pytest.mark.parametrize("provider", ["anthropic", "openai", "ollama"])
def test_call_llm_returns_on_first_valid_response(provider):
    target = f"llm._call_{provider}"
    with patch(target, return_value=VALID_RESPONSE) as mock_fn:
        result = call_llm(provider, "model", "sys", "usr", required_keys=REQUIRED_KEYS)
    assert result == {"match": "yes", "if_yes_reason": "ok", "suggestions": ""}
    mock_fn.assert_called_once_with("model", "sys", "usr")


# ---------------------------------------------------------------------------
# call_llm — retry on invalid JSON
# ---------------------------------------------------------------------------

def test_call_llm_retries_on_invalid_json_then_succeeds():
    responses = iter(["not-json", "still-not-json", '{"key": "val"}'])
    with patch("llm._call_anthropic", side_effect=lambda *_: next(responses)):
        result = call_llm("anthropic", "model", "sys", "usr")
    assert result == {"key": "val"}


def test_call_llm_raises_after_exhausting_retries_on_bad_json():
    with patch("llm._call_anthropic", return_value="not-json"):
        with pytest.raises(RuntimeError, match="3 attempts"):
            call_llm("anthropic", "model", "sys", "usr")


# ---------------------------------------------------------------------------
# call_llm — retry on missing required keys
# ---------------------------------------------------------------------------

def test_call_llm_retries_when_keys_missing_then_succeeds():
    responses = iter(['{"a": 1}', '{"a": 1}', '{"a": 1, "b": 2}'])
    with patch("llm._call_anthropic", side_effect=lambda *_: next(responses)):
        result = call_llm("anthropic", "model", "sys", "usr", required_keys=["a", "b"])
    assert result == {"a": 1, "b": 2}


def test_call_llm_raises_after_exhausting_retries_on_missing_keys():
    with patch("llm._call_anthropic", return_value='{"a": 1}'):
        with pytest.raises(RuntimeError, match="3 attempts"):
            call_llm("anthropic", "model", "sys", "usr", required_keys=["a", "b"])


def test_call_llm_no_required_keys_returns_any_valid_json():
    with patch("llm._call_anthropic", return_value='{"whatever": true}'):
        result = call_llm("anthropic", "model", "sys", "usr")
    assert result == {"whatever": True}


# ---------------------------------------------------------------------------
# Fail-fast guards on missing API keys
# ---------------------------------------------------------------------------

def test_get_anthropic_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr(llm_module, "_anthropic", None)
    monkeypatch.setattr(llm_module, "ANTHROPIC_API_KEY", "")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm_module._get_anthropic()


def test_get_openai_raises_when_key_missing(monkeypatch):
    monkeypatch.setattr(llm_module, "_openai", None)
    monkeypatch.setattr(llm_module, "OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        llm_module._get_openai()
