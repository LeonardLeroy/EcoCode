from __future__ import annotations

import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from ecocode.core.optimizer import OptimizationSuggestion


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
    if not model.strip():
        raise ValueError("optimize.llm.model must be set when optimize.llm.enabled is true")

    source = script_path.read_text(encoding="utf-8", errors="replace")
    payload = {
        "model": model,
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
        "http://127.0.0.1:11434/api/generate",
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
