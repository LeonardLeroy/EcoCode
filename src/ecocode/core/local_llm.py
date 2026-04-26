from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from ecocode.core.optimizer import OptimizationSuggestion


DEFAULT_OLLAMA_CODING_MODEL = "qwen2.5-coder:7b"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"
OLLAMA_BASE_URL_ENV_VAR = "ECOCODE_OLLAMA_BASE_URL"
DISCOURAGED_OLLAMA_MODELS = {"granite3.1-moe", "granite3.1-moe:latest"}
PREFERRED_OLLAMA_MODELS = (
    "qwen2.5-coder:32b",
    "qwen2.5-coder:14b",
    "qwen2.5-coder:7b",
    "deepseek-coder-v2:16b",
    "deepseek-coder:6.7b",
    "codellama:13b",
    "codellama:7b",
)


def _ollama_url(path: str) -> str:
    base_url = os.getenv(OLLAMA_BASE_URL_ENV_VAR, DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
    if not base_url:
        base_url = DEFAULT_OLLAMA_BASE_URL
    return f"{base_url}{path}"


def fetch_local_llm_suggestions(
    script_path: Path,
    provider: str,
    model: str,
    max_suggestions: int,
    timeout_seconds: float,
) -> list[OptimizationSuggestion]:
    if max_suggestions <= 0:
        raise ValueError("max_suggestions must be greater than 0")

    normalized_provider = provider.strip().lower()
    if normalized_provider in {"", "none"}:
        return []

    if normalized_provider != "ollama":
        raise ValueError(f"Unsupported local LLM provider: {provider}")
    resolved_model = resolve_ollama_model(model, timeout_seconds=timeout_seconds)

    source = script_path.read_text(encoding="utf-8", errors="replace")
    payload = {
        "model": resolved_model,
        "stream": False,
        "format": "json",
        "prompt": (
            "You are a code optimization assistant. "
            "Return strict JSON only with this shape: "
            "{\"suggestions\":[{\"rule_id\":\"LLM001\",\"title\":\"...\","
            "\"rationale\":\"...\",\"impact\":\"low|medium|high\","
            "\"confidence\":0.0,\"language\":\"python\"}]}"
            " Limit to max_suggestions items and suggest only behavior-preserving changes."
            f" max_suggestions={max_suggestions}.\n\n"
            f"SOURCE:\n{source}"
        ),
    }

    request = Request(
        _ollama_url("/api/generate"),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"Failed to reach local LLM provider: {exc}") from exc

    raw_response = str(response_payload.get("response", "")).strip()
    if not raw_response:
        return []

    parsed = json.loads(raw_response)
    raw_items = parsed.get("suggestions", []) if isinstance(parsed, dict) else parsed
    if not isinstance(raw_items, list):
        return []

    suggestions: list[OptimizationSuggestion] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue

        impact = str(item.get("impact", "medium")).strip().lower()
        if impact not in {"low", "medium", "high"}:
            impact = "medium"

        try:
            confidence = float(item.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = max(0.0, min(1.0, confidence))

        suggestions.append(
            OptimizationSuggestion(
                rule_id=str(item.get("rule_id", "LLM001")).strip() or "LLM001",
                title=str(item.get("title", "LLM suggestion")).strip() or "LLM suggestion",
                rationale=str(item.get("rationale", "Local LLM suggested this optimization.")).strip()
                or "Local LLM suggested this optimization.",
                impact=impact,
                confidence=confidence,
                language=str(item.get("language", "python")).strip() or "python",
            )
        )

        if len(suggestions) >= max_suggestions:
            break

    return suggestions


def fetch_local_llm_candidate_patch(
    script_path: Path,
    provider: str,
    model: str,
    timeout_seconds: float,
) -> tuple[str, str]:
    normalized_provider = provider.strip().lower()
    if normalized_provider in {"", "none"}:
        raise ValueError("Local LLM provider is disabled by configuration")
    if normalized_provider != "ollama":
        raise ValueError(f"Unsupported local LLM provider: {provider}")

    resolved_model = resolve_ollama_model(model, timeout_seconds=timeout_seconds)
    source = script_path.read_text(encoding="utf-8", errors="replace")

    payload = {
        "model": resolved_model,
        "stream": False,
        "format": "json",
        "prompt": (
            "You are a code optimization assistant. "
            "Return strict JSON only with this shape: "
            "{\"strategy_title\":\"...\",\"candidate_source\":\"...\"}. "
            "Preserve behavior and output full candidate source text."
            f"\n\nSOURCE:\n{source}"
        ),
    }

    request = Request(
        _ollama_url("/api/generate"),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"Failed to reach local LLM provider: {exc}") from exc

    raw_response = str(response_payload.get("response", "")).strip()
    if not raw_response:
        raise ValueError("Local LLM returned an empty candidate patch response")

    parsed = json.loads(raw_response)
    if not isinstance(parsed, dict):
        raise ValueError("Local LLM candidate response must be a JSON object")

    candidate_source = str(parsed.get("candidate_source", ""))
    if not candidate_source.strip():
        raise ValueError("Local LLM candidate response did not include candidate_source")

    strategy_title = str(parsed.get("strategy_title", "LLM behavior-preserving optimization")).strip()
    if not strategy_title:
        strategy_title = "LLM behavior-preserving optimization"

    return candidate_source, strategy_title


def resolve_ollama_model(requested_model: str, timeout_seconds: float) -> str:
    normalized_requested = requested_model.strip().lower()

    if normalized_requested and normalized_requested not in DISCOURAGED_OLLAMA_MODELS:
        return requested_model.strip()

    available = list_ollama_models(timeout_seconds=timeout_seconds)
    available_map = {name.lower(): name for name in available}

    for preferred in PREFERRED_OLLAMA_MODELS:
        matched = available_map.get(preferred.lower())
        if matched is not None:
            return matched

    for name in available:
        if name.lower() not in DISCOURAGED_OLLAMA_MODELS:
            return name

    return DEFAULT_OLLAMA_CODING_MODEL


def list_ollama_models(timeout_seconds: float) -> list[str]:
    request = Request(
        _ollama_url("/api/tags"),
        headers={"Content-Type": "application/json"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except URLError:
        return []

    raw_models = payload.get("models", []) if isinstance(payload, dict) else []
    if not isinstance(raw_models, list):
        return []

    names: list[str] = []
    for item in raw_models:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        names.append(name)
    return names
