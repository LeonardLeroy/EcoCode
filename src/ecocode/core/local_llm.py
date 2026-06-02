from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from ecocode.core.optimizer import OptimizationSuggestion, _detect_language


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

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_LLM_API_KEY_ENV_VAR = "ECOCODE_LLM_API_KEY"


def _ollama_url(path: str) -> str:
    base_url = os.getenv(OLLAMA_BASE_URL_ENV_VAR, DEFAULT_OLLAMA_BASE_URL).strip().rstrip("/")
    if not base_url:
        base_url = DEFAULT_OLLAMA_BASE_URL
    return f"{base_url}{path}"


def _extract_json(raw: str) -> Any:
    """Parse JSON from a model response that may include fences or prose."""
    text = raw.strip()
    if not text:
        raise json.JSONDecodeError("Empty LLM response", raw, 0)

    if text.startswith("```"):
        # Drop the opening fence (``` or ```json) and any trailing fence.
        text = text.split("\n", 1)[1] if "\n" in text else ""
        fence_index = text.rfind("```")
        if fence_index != -1:
            text = text[:fence_index]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise json.JSONDecodeError("No JSON payload found in LLM response", raw, 0)


def _build_suggest_prompt(
    source: str,
    language: str,
    max_suggestions: int,
    known_findings: list[str] | None,
) -> str:
    findings_line = ""
    if known_findings:
        findings_line = (
            "Static analysis already flagged: "
            + ", ".join(known_findings)
            + ". Confirm or extend these and add new ones.\n"
        )
    return (
        "You are a code optimization assistant focused on reducing CPU, memory and energy use.\n"
        f"Language: {language}.\n"
        f"{findings_line}"
        "Return STRICT JSON only, no prose, of this exact shape:\n"
        '{"suggestions":[{"rule_id":"LLM001","title":"...","rationale":"...",'
        '"impact":"low|medium|high","confidence":0.0,'
        f'"language":"{language}","line":1}}]}}\n'
        f"Return at most {max_suggestions} behavior-preserving suggestions. "
        'Set "line" to the 1-based line number of the relevant code.\n\n'
        f"SOURCE:\n{source}"
    )


def _build_patch_prompt(source: str, language: str) -> str:
    return (
        "You are a code optimization assistant.\n"
        f"Language: {language}.\n"
        "Return STRICT JSON only of this shape: "
        '{"strategy_title":"...","candidate_source":"..."}. '
        "Preserve behavior exactly and output the FULL candidate source text.\n\n"
        f"SOURCE:\n{source}"
    )


def _generate(
    provider: str,
    prompt: str,
    model: str,
    timeout_seconds: float,
    api_key_env: str,
) -> str:
    if provider == "ollama":
        return _generate_ollama(prompt, model, timeout_seconds)
    if provider == "anthropic":
        return _generate_anthropic(prompt, model, timeout_seconds, api_key_env)
    raise ValueError(f"Unsupported local LLM provider: {provider}")


def _generate_ollama(prompt: str, model: str, timeout_seconds: float) -> str:
    resolved_model = resolve_ollama_model(model, timeout_seconds=timeout_seconds)
    payload = {
        "model": resolved_model,
        "stream": False,
        "format": "json",
        "prompt": prompt,
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

    return str(response_payload.get("response", "")).strip()


def _generate_anthropic(
    prompt: str,
    model: str,
    timeout_seconds: float,
    api_key_env: str,
) -> str:
    api_key = os.getenv(api_key_env, "").strip()
    if not api_key:
        raise RuntimeError(
            f"Remote LLM API key not set; export it in the {api_key_env} environment variable"
        )

    model_id = model.strip()
    if not model_id or not model_id.startswith("claude"):
        model_id = DEFAULT_ANTHROPIC_MODEL

    payload = {
        "model": model_id,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    request = Request(
        ANTHROPIC_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"Failed to reach remote LLM provider: {exc}") from exc

    parts = response_payload.get("content", []) if isinstance(response_payload, dict) else []
    if not isinstance(parts, list):
        return ""
    text = "".join(
        str(part.get("text", ""))
        for part in parts
        if isinstance(part, dict) and part.get("type") == "text"
    )
    return text.strip()


def fetch_local_llm_suggestions(
    script_path: Path,
    provider: str,
    model: str,
    max_suggestions: int,
    timeout_seconds: float,
    known_findings: list[str] | None = None,
    api_key_env: str = DEFAULT_LLM_API_KEY_ENV_VAR,
) -> list[OptimizationSuggestion]:
    if max_suggestions <= 0:
        raise ValueError("max_suggestions must be greater than 0")

    normalized_provider = provider.strip().lower()
    if normalized_provider in {"", "none"}:
        return []

    source = script_path.read_text(encoding="utf-8", errors="replace")
    language = _detect_language(script_path.suffix.lower())
    prompt = _build_suggest_prompt(source, language, max_suggestions, known_findings)

    raw_response = _generate(
        normalized_provider, prompt, model, timeout_seconds, api_key_env
    )
    if not raw_response:
        return []

    parsed = _extract_json(raw_response)
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

        line_value = item.get("line")
        try:
            line = int(line_value) if line_value is not None else None
        except (TypeError, ValueError):
            line = None
        if line is not None and line < 1:
            line = None

        suggestions.append(
            OptimizationSuggestion(
                rule_id=str(item.get("rule_id", "LLM001")).strip() or "LLM001",
                title=str(item.get("title", "LLM suggestion")).strip() or "LLM suggestion",
                rationale=str(item.get("rationale", "Local LLM suggested this optimization.")).strip()
                or "Local LLM suggested this optimization.",
                impact=impact,
                confidence=confidence,
                language=str(item.get("language", language)).strip() or language,
                line=line,
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
    api_key_env: str = DEFAULT_LLM_API_KEY_ENV_VAR,
) -> tuple[str, str]:
    normalized_provider = provider.strip().lower()
    if normalized_provider in {"", "none"}:
        raise ValueError("Local LLM provider is disabled by configuration")

    source = script_path.read_text(encoding="utf-8", errors="replace")
    language = _detect_language(script_path.suffix.lower())
    prompt = _build_patch_prompt(source, language)

    raw_response = _generate(
        normalized_provider, prompt, model, timeout_seconds, api_key_env
    )
    if not raw_response:
        raise ValueError("Local LLM returned an empty candidate patch response")

    parsed = _extract_json(raw_response)
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
