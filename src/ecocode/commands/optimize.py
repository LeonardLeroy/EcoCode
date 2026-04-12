from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.config import load_project_config
from ecocode.core.optimizer import generate_optimization_patch, suggest_optimizations
from ecocode.core.profiler import (
    DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
    profile_script_repeated,
    summarize_profile_runs,
)
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

    patch_parser = optimize_subparsers.add_parser(
        "patch",
        help="Generate a candidate patch from a selected optimization strategy",
    )
    patch_parser.add_argument("script", help="Path to the source file")
    patch_parser.add_argument(
        "--rule-id",
        default=None,
        help="Apply a specific rule ID (default: first patchable suggestion)",
    )
    patch_parser.add_argument(
        "--output",
        default=None,
        help="Output path for candidate file (default: <script>.candidate<suffix>)",
    )
    patch_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output file if it already exists",
    )
    patch_parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    patch_parser.set_defaults(handler=handle_patch)

    evaluate_parser = optimize_subparsers.add_parser(
        "evaluate",
        help="Evaluate a candidate script against an existing baseline",
    )
    evaluate_parser.add_argument(
        "--baseline",
        required=True,
        help="Path to a baseline JSON file (from baseline create)",
    )
    evaluate_parser.add_argument(
        "--candidate",
        required=True,
        help="Path to candidate source file",
    )
    evaluate_parser.add_argument(
        "--collector",
        choices=["placeholder", "runtime"],
        default="placeholder",
        help="Collector backend to use (default: placeholder)",
    )
    evaluate_parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Repeat candidate profiling multiple times before compare",
    )
    evaluate_parser.add_argument(
        "--sampling-interval",
        type=float,
        default=DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
        help="Sampling interval in seconds for runtime collectors",
    )
    evaluate_parser.add_argument(
        "--energy-threshold-pct",
        type=float,
        default=None,
        help="Allowed energy increase percentage before failing",
    )
    evaluate_parser.add_argument(
        "--max-energy-cv-pct",
        type=float,
        default=None,
        help="Maximum allowed coefficient of variation (%%) for candidate energy over runs",
    )
    evaluate_parser.add_argument(
        "--fail-on-unstable",
        action="store_true",
        help="Return non-zero if candidate run variability exceeds stability threshold",
    )
    evaluate_parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    evaluate_parser.set_defaults(handler=handle_evaluate)


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


def _default_candidate_output_path(script_path: Path) -> Path:
    candidate_name = f"{script_path.stem}.candidate{script_path.suffix}"
    return script_path.with_name(candidate_name)


def handle_patch(args: argparse.Namespace) -> int:
    config = load_project_config(Path.cwd())
    if not config.optimize_enabled:
        print("optimize patch is disabled by the current optimize policy")
        return 1

    script_path = Path(args.script).resolve()
    output_path = (
        Path(args.output).resolve()
        if args.output is not None
        else _default_candidate_output_path(script_path)
    )

    try:
        result = generate_optimization_patch(
            script_path=script_path,
            output_path=output_path,
            rule_id=args.rule_id,
            overwrite=args.overwrite,
            allowed_patch_rule_ids=config.optimize_allowed_patch_rule_ids,
            default_patch_rule_id=config.optimize_default_patch_rule_id,
            max_patch_changes=config.optimize_max_patch_changes,
        )
    except (FileNotFoundError, ValueError, UnicodeError) as exc:
        print(str(exc))
        return 1

    payload = {
        "schemaVersion": CURRENT_SCHEMA_VERSION,
        "command": "optimize patch",
        "script": result.script,
        "candidate_path": result.candidate_path,
        "rule_id": result.rule_id,
        "strategy_title": result.strategy_title,
        "applied": result.applied,
        "changes_count": result.changes_count,
        "diff": result.diff,
    }

    try:
        validate_named_schema("optimize_patch_report", payload)
    except SchemaValidationError as exc:
        print(f"Output schema validation failed: {exc}")
        return 1

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print("EcoCode optimize patch")
    print(f"Script:                 {result.script}")
    print(f"Candidate file:         {result.candidate_path}")
    print(f"Rule:                   {result.rule_id}")
    print(f"Strategy:               {result.strategy_title}")
    print(f"Applied changes:        {result.changes_count}")
    if result.diff:
        print("Diff preview:")
        print(result.diff)
    return 0


def handle_evaluate(args: argparse.Namespace) -> int:
    baseline_path = Path(args.baseline).resolve()
    candidate_path = Path(args.candidate).resolve()
    config = load_project_config(Path.cwd())

    if args.runs <= 0:
        print("--runs must be greater than 0")
        return 1

    if not baseline_path.exists() or not baseline_path.is_file():
        print(f"Baseline file not found: {baseline_path}")
        return 1

    try:
        baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Failed to read baseline file: {exc}")
        return 1

    baseline = baseline_data.get("baseline", {})
    baseline_stats = baseline_data.get("statistics", {})
    baseline_energy = float(
        baseline_stats.get(
            "estimated_energy_wh_median",
            baseline.get("estimated_energy_wh", 0.0),
        )
    )

    try:
        candidate_runs = profile_script_repeated(
            candidate_path,
            collector=args.collector,
            runs=args.runs,
            cpu_energy_factor=config.calibration_cpu_wh_per_cpu_second,
            memory_energy_factor=config.calibration_memory_wh_per_mb,
            sampling_interval_seconds=args.sampling_interval,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    candidate_last = candidate_runs[-1]
    candidate_summary = summarize_profile_runs(candidate_runs)
    candidate_energy = float(candidate_summary.estimated_energy_wh_median)

    increase_pct = 0.0
    if baseline_energy > 0:
        increase_pct = ((candidate_energy - baseline_energy) / baseline_energy) * 100.0

    threshold_pct = args.energy_threshold_pct
    if threshold_pct is None:
        threshold_pct = config.baseline_energy_threshold_pct

    candidate_energy_cv_pct = 0.0
    if candidate_summary.estimated_energy_wh_mean > 0:
        candidate_energy_cv_pct = round(
            (
                candidate_summary.estimated_energy_wh_stddev
                / candidate_summary.estimated_energy_wh_mean
            )
            * 100.0,
            6,
        )

    stability_threshold = args.max_energy_cv_pct
    if stability_threshold is None:
        stability_threshold = config.stability_max_energy_cv_pct
    if stability_threshold < 0:
        print("--max-energy-cv-pct must be greater than or equal to 0")
        return 1

    unstable = args.runs > 1 and candidate_energy_cv_pct > stability_threshold
    regression = increase_pct > threshold_pct

    payload = {
        "schemaVersion": CURRENT_SCHEMA_VERSION,
        "command": "optimize evaluate",
        "baseline_path": str(baseline_path),
        "candidate_path": str(candidate_path),
        "collector": args.collector,
        "runs": args.runs,
        "threshold_pct": threshold_pct,
        "baseline_energy_wh": baseline_energy,
        "candidate_energy_wh": candidate_energy,
        "increase_pct": round(increase_pct, 4),
        "regression": regression,
        "status": "failed" if regression else "passed",
        "candidate": {
            "script": candidate_last.script,
            "cpu_seconds": candidate_last.cpu_seconds,
            "memory_mb": candidate_last.memory_mb,
            "estimated_energy_wh": candidate_last.estimated_energy_wh,
            "sustainability_score": candidate_last.sustainability_score,
        },
        "candidate_statistics": {
            "estimated_energy_wh_mean": candidate_summary.estimated_energy_wh_mean,
            "estimated_energy_wh_median": candidate_summary.estimated_energy_wh_median,
            "estimated_energy_wh_stddev": candidate_summary.estimated_energy_wh_stddev,
            "estimated_energy_wh_cv_pct": candidate_energy_cv_pct,
            "cpu_seconds_median": candidate_summary.cpu_seconds_median,
            "memory_mb_median": candidate_summary.memory_mb_median,
        },
        "stability": {
            "max_energy_cv_pct": stability_threshold,
            "unstable": unstable,
        },
    }

    try:
        validate_named_schema("optimize_evaluate_report", payload)
    except SchemaValidationError as exc:
        print(f"Output schema validation failed: {exc}")
        return 1

    if args.json:
        print(json.dumps(payload, indent=2))
        if args.fail_on_unstable and unstable:
            return 3
        return 2 if regression else 0

    print("EcoCode optimize evaluate")
    print(f"Baseline file:          {baseline_path}")
    print(f"Candidate file:         {candidate_path}")
    print(f"Baseline energy Wh:     {baseline_energy}")
    print(f"Candidate energy Wh:    {candidate_energy}")
    print(f"Energy increase (%):    {round(increase_pct, 4)}")
    print(f"Threshold (%):          {threshold_pct}")
    if args.runs > 1:
        print(f"Energy CV (%):          {candidate_energy_cv_pct}")
        print(f"Stability limit (%):    {stability_threshold}")
        if unstable:
            print("Stability:              UNSTABLE")
            if args.fail_on_unstable:
                return 3

    if regression:
        print("Status:                 FAILED (candidate regression)")
        return 2

    print("Status:                 PASSED")
    return 0
