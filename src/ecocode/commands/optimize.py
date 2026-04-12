from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.optimizer import suggest_optimizations
from ecocode.core.schemas import (
    CURRENT_SCHEMA_VERSION,
    SchemaValidationError,
    validate_named_schema,
)


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "optimize",
        help="Optimizer commands (suggestions and candidate evaluation)",
    )
    optimize_subparsers = parser.add_subparsers(dest="optimize_command")

    suggest_parser = optimize_subparsers.add_parser(
        "suggest",
        help="Generate optimization suggestions for a source file",
    )
    suggest_parser.add_argument("script", help="Path to the source file")
    suggest_parser.add_argument(
        "--max-suggestions",
        type=int,
        default=10,
        help="Maximum number of suggestions to return",
    )
    suggest_parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    suggest_parser.set_defaults(handler=handle_suggest)


def handle_suggest(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()

    try:
        suggestions = suggest_optimizations(
            script_path=script_path,
            max_suggestions=args.max_suggestions,
        )
    except (FileNotFoundError, ValueError, UnicodeError) as exc:
        print(str(exc))
        return 1

    payload = {
        "schemaVersion": CURRENT_SCHEMA_VERSION,
        "command": "optimize suggest",
        "script": str(script_path),
        "suggestion_count": len(suggestions),
        "suggestions": [
            {
                "rule_id": item.rule_id,
                "title": item.title,
                "rationale": item.rationale,
                "impact": item.impact,
                "confidence": item.confidence,
                "language": item.language,
            }
            for item in suggestions
        ],
    }

    try:
        validate_named_schema("optimize_suggest_report", payload)
    except SchemaValidationError as exc:
        print(f"Output schema validation failed: {exc}")
        return 1

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print("EcoCode optimize suggest")
    print(f"Script:                 {script_path}")
    print(f"Suggestions:            {len(suggestions)}")
    if not suggestions:
        print("No suggestions found. Consider running benchmark and profile commands first.")
        return 0

    for index, item in enumerate(suggestions, start=1):
        print(f"{index}. [{item.rule_id}] {item.title}")
        print(f"   Impact: {item.impact} | Confidence: {item.confidence} | Language: {item.language}")
        print(f"   Why: {item.rationale}")

    return 0
