from __future__ import annotations

from pathlib import Path

import pytest

from ecocode.core import local_llm
from ecocode.core.local_llm import _extract_json, fetch_local_llm_suggestions


def test_extract_json_handles_code_fences() -> None:
    raw = '```json\n{"suggestions": []}\n```'
    assert _extract_json(raw) == {"suggestions": []}


def test_extract_json_handles_surrounding_prose() -> None:
    raw = 'Sure! Here it is: {"suggestions": [{"title": "x"}]} hope it helps'
    parsed = _extract_json(raw)
    assert parsed["suggestions"][0]["title"] == "x"


def test_fetch_suggestions_parses_noisy_response(tmp_path: Path, monkeypatch) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hi')\n", encoding="utf-8")

    noisy = (
        "Here are my suggestions:\n"
        '{"suggestions":[{"rule_id":"LLM001","title":"Cache result",'
        '"rationale":"reuse","impact":"high","confidence":0.9,"line":1}]}'
    )
    monkeypatch.setattr(local_llm, "_generate", lambda *a, **k: noisy)

    suggestions = fetch_local_llm_suggestions(
        script_path=script,
        provider="ollama",
        model="qwen2.5-coder:7b",
        max_suggestions=3,
        timeout_seconds=1.0,
    )

    assert len(suggestions) == 1
    assert suggestions[0].rule_id == "LLM001"
    assert suggestions[0].line == 1
    assert suggestions[0].language == "python"


def test_anthropic_provider_requires_api_key(tmp_path: Path, monkeypatch) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hi')\n", encoding="utf-8")

    monkeypatch.delenv("ECOCODE_LLM_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="API key"):
        fetch_local_llm_suggestions(
            script_path=script,
            provider="anthropic",
            model="claude-sonnet-4-6",
            max_suggestions=3,
            timeout_seconds=1.0,
        )
