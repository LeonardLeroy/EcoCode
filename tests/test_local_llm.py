from __future__ import annotations

from ecocode.core.local_llm import DEFAULT_OLLAMA_CODING_MODEL, resolve_ollama_model


def test_resolve_ollama_model_keeps_explicit_non_discouraged_model() -> None:
    model = resolve_ollama_model(requested_model="qwen2.5-coder:14b", timeout_seconds=1.0)
    assert model == "qwen2.5-coder:14b"


def test_resolve_ollama_model_avoids_granite(monkeypatch) -> None:
    monkeypatch.setattr(
        "ecocode.core.local_llm.list_ollama_models",
        lambda timeout_seconds: ["granite3.1-moe:latest", "qwen2.5-coder:7b"],
    )

    model = resolve_ollama_model(requested_model="granite3.1-moe", timeout_seconds=1.0)
    assert model == "qwen2.5-coder:7b"


def test_resolve_ollama_model_falls_back_to_default_when_no_models(monkeypatch) -> None:
    monkeypatch.setattr(
        "ecocode.core.local_llm.list_ollama_models",
        lambda timeout_seconds: [],
    )

    model = resolve_ollama_model(requested_model="", timeout_seconds=1.0)
    assert model == DEFAULT_OLLAMA_CODING_MODEL
