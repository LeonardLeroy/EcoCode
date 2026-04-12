from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OptimizationSuggestion:
    rule_id: str
    title: str
    rationale: str
    impact: str
    confidence: float
    language: str


def suggest_optimizations(script_path: Path, max_suggestions: int = 10) -> list[OptimizationSuggestion]:
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")
    if max_suggestions <= 0:
        raise ValueError("max_suggestions must be greater than 0")

    source = script_path.read_text(encoding="utf-8", errors="replace")
    suffix = script_path.suffix.lower()
    language = _detect_language(suffix)

    suggestions: list[OptimizationSuggestion] = []
    suggestions.extend(_generic_rules(source, language))

    if language == "python":
        suggestions.extend(_python_rules(source))
    elif language in {"javascript", "typescript"}:
        suggestions.extend(_js_rules(source, language))
    elif language in {"c", "cpp", "csharp", "rust"}:
        suggestions.extend(_native_rules(source, language))
    elif language in {"html", "css"}:
        suggestions.extend(_web_rules(source, language))
    elif language == "assembly":
        suggestions.extend(_asm_rules(source))

    deduped: list[OptimizationSuggestion] = []
    seen: set[str] = set()
    for item in suggestions:
        key = f"{item.rule_id}:{item.title}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_suggestions:
            break

    return deduped


def _detect_language(suffix: str) -> str:
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".c": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".cs": "csharp",
        ".rs": "rust",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".s": "assembly",
        ".asm": "assembly",
    }
    return mapping.get(suffix, "unknown")


def _generic_rules(source: str, language: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []
    lines = source.splitlines()

    if len(lines) > 800:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="GEN001",
                title="Split very large file",
                rationale="Large files are harder to optimize and often hide duplicated work.",
                impact="medium",
                confidence=0.72,
                language=language,
            )
        )

    if source.count("TODO") >= 5:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="GEN002",
                title="Review deferred hot-path TODOs",
                rationale="Many TODO markers may indicate pending performance-sensitive code paths.",
                impact="low",
                confidence=0.55,
                language=language,
            )
        )

    return suggestions


def _python_rules(source: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if re.search(r"for\s+\w+\s+in\s+range\(len\(", source):
        suggestions.append(
            OptimizationSuggestion(
                rule_id="PY001",
                title="Prefer direct iteration over range(len())",
                rationale="Index-based loops can add overhead and reduce readability in Python.",
                impact="medium",
                confidence=0.84,
                language="python",
            )
        )

    if re.search(r"\+\=\s*['\"]", source):
        suggestions.append(
            OptimizationSuggestion(
                rule_id="PY002",
                title="Avoid repeated string concatenation",
                rationale="Repeated string concatenation may cause unnecessary allocations; prefer join/buffer patterns.",
                impact="medium",
                confidence=0.78,
                language="python",
            )
        )

    if source.count("for ") >= 2 and source.count("range(") >= 2:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="PY003",
                title="Check nested loops for algorithmic complexity",
                rationale="Nested loops are common hotspots; evaluate data structures and loop bounds.",
                impact="high",
                confidence=0.7,
                language="python",
            )
        )

    return suggestions


def _js_rules(source: str, language: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if "forEach(" in source and "await " in source:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="JS001",
                title="Avoid async work inside forEach",
                rationale="async forEach patterns may be suboptimal; consider for...of with await control.",
                impact="medium",
                confidence=0.75,
                language=language,
            )
        )

    if re.search(r"new\s+Array\(\d+\)", source):
        suggestions.append(
            OptimizationSuggestion(
                rule_id="JS002",
                title="Validate large array preallocation",
                rationale="Large preallocated arrays can increase memory pressure.",
                impact="medium",
                confidence=0.66,
                language=language,
            )
        )

    return suggestions


def _native_rules(source: str, language: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if source.count("for (") + source.count("for(") >= 2:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="NAT001",
                title="Review nested/native loops",
                rationale="Nested loops in native code often dominate runtime and energy usage.",
                impact="high",
                confidence=0.73,
                language=language,
            )
        )

    if "malloc(" in source or "new " in source:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="NAT002",
                title="Inspect allocation churn",
                rationale="Frequent allocations can increase CPU and memory overhead.",
                impact="medium",
                confidence=0.68,
                language=language,
            )
        )

    return suggestions


def _web_rules(source: str, language: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if language == "html" and "style=" in source:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="WEB001",
                title="Reduce inline style duplication",
                rationale="Heavy inline styles can duplicate declarations and increase page weight.",
                impact="low",
                confidence=0.71,
                language=language,
            )
        )

    if language == "css" and source.count("box-shadow") >= 3:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="WEB002",
                title="Review expensive paint effects",
                rationale="Multiple heavy shadows may increase rendering cost on low-power devices.",
                impact="medium",
                confidence=0.64,
                language=language,
            )
        )

    return suggestions


def _asm_rules(source: str) -> list[OptimizationSuggestion]:
    suggestions: list[OptimizationSuggestion] = []

    if source.lower().count("mov") >= 20:
        suggestions.append(
            OptimizationSuggestion(
                rule_id="ASM001",
                title="Review register move density",
                rationale="High move density can indicate opportunities for instruction simplification.",
                impact="medium",
                confidence=0.6,
                language="assembly",
            )
        )

    return suggestions
