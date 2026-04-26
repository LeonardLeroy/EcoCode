from __future__ import annotations

from ecocode.core import local_llm
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


def test_list_ollama_models_uses_configurable_base_url(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class _DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b'{"models": []}'

    def _fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        return _DummyResponse()

    monkeypatch.setenv(local_llm.OLLAMA_BASE_URL_ENV_VAR, "https://ollama.example")
    monkeypatch.setattr("ecocode.core.local_llm.urlopen", _fake_urlopen)

    assert local_llm.list_ollama_models(timeout_seconds=1.0) == []
    assert captured["url"] == "https://ollama.example/api/tags"
