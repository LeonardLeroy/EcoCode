from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.config import load_project_config
from ecocode.core.history import should_save_run, write_audit_run
from ecocode.core.profiler import (
    ProfileResult,
    profile_script_repeated,
    summarize_profile_runs,
)
from ecocode.core.schemas import SchemaValidationError, validate_named_schema


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "baseline",
        help="Create and compare energy profile baselines",
    )
    baseline_subparsers = parser.add_subparsers(dest="baseline_command")

    create_parser = baseline_subparsers.add_parser(
        "create",
        help="Create a baseline report from a script",
    )
    create_parser.add_argument("script", help="Path to the script to profile")
    create_parser.add_argument(
        "--collector",
        choices=["placeholder", "runtime"],
        default="placeholder",
        help="Collector backend to use (default: placeholder)",
    )
    create_parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output path for the baseline JSON file",
    )
    create_parser.add_argument(
        "--save-run",
        action="store_true",
        help="Save this audit result to the local history directory",
    )
    create_parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Repeat profiling multiple times and store summary",
    )
    create_parser.set_defaults(handler=handle_create)

    compare_parser = baseline_subparsers.add_parser(
        "compare",
        help="Compare current script profile against a baseline",
    )
    compare_parser.add_argument("script", help="Path to the script to profile")
    compare_parser.add_argument(
        "--collector",
        choices=["placeholder", "runtime"],
        default="placeholder",
        help="Collector backend to use (default: placeholder)",
    )
    compare_parser.add_argument(
        "--baseline",
        required=True,
        help="Path to a baseline JSON file",
    )
    compare_parser.add_argument(
        "--energy-threshold-pct",
        type=float,
        default=None,
        help="Allowed energy increase percentage before failing",
    )
    compare_parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    compare_parser.add_argument(
        "--save-run",
        action="store_true",
        help="Save this audit result to the local history directory",
    )
    compare_parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Repeat current profiling multiple times before compare",
    )
    compare_parser.add_argument(
        "--max-energy-cv-pct",
        type=float,
        default=None,
        help="Maximum allowed coefficient of variation (%%) for energy over runs",
    )
    compare_parser.add_argument(
        "--fail-on-unstable",
        action="store_true",
        help="Return non-zero if run variability exceeds stability threshold",
    )
    compare_parser.set_defaults(handler=handle_compare)


def _result_to_dict(result: ProfileResult) -> dict[str, float | int | str]:
    return {
        "script": result.script,
        "cpu_seconds": result.cpu_seconds,
        "memory_mb": result.memory_mb,
        "estimated_energy_wh": result.estimated_energy_wh,
        "sustainability_score": result.sustainability_score,
    }


def handle_create(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()
    output_path = Path(args.output).resolve()
    config = load_project_config(Path.cwd())

    if args.runs <= 0:
        print("--runs must be greater than 0")
        return 1

    try:
        results = profile_script_repeated(
            script_path,
            collector=args.collector,
            runs=args.runs,
            cpu_energy_factor=config.calibration_cpu_wh_per_cpu_second,
            memory_energy_factor=config.calibration_memory_wh_per_mb,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    result = results[-1]
    summary = summarize_profile_runs(results)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 2,
        "collector": args.collector,
        "runs": args.runs,
        "baseline": _result_to_dict(result),
        "statistics": {
            "estimated_energy_wh_mean": summary.estimated_energy_wh_mean,
            "estimated_energy_wh_median": summary.estimated_energy_wh_median,
            "estimated_energy_wh_stddev": summary.estimated_energy_wh_stddev,
            "cpu_seconds_median": summary.cpu_seconds_median,
            "memory_mb_median": summary.memory_mb_median,
        },
    }
    try:
        validate_named_schema("baseline_file", payload)
    except SchemaValidationError as exc:
        print(f"Output schema validation failed: {exc}")
        return 1
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if config.history_enabled and should_save_run(args.save_run, config.history_auto_save):
        write_audit_run(
            project_root=config.project_root,
            history_dir=config.history_dir,
            command_name="baseline-create",
            payload={
                "command": "baseline create",
                "output": str(output_path),
                "result": payload,
            },
        )

    print(f"Baseline created: {output_path}")
    return 0


def handle_compare(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()
    baseline_path = Path(args.baseline).resolve()
    config = load_project_config(Path.cwd())

    if args.runs <= 0:
        print("--runs must be greater than 0")
        return 1

    try:
        current_runs = profile_script_repeated(
            script_path,
            collector=args.collector,
            runs=args.runs,
            cpu_energy_factor=config.calibration_cpu_wh_per_cpu_second,
            memory_energy_factor=config.calibration_memory_wh_per_mb,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    current = current_runs[-1]
    current_summary = summarize_profile_runs(current_runs)
    current_energy_cv_pct = 0.0
    if current_summary.estimated_energy_wh_mean > 0:
        current_energy_cv_pct = round(
            (
                current_summary.estimated_energy_wh_stddev
                / current_summary.estimated_energy_wh_mean
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
    unstable = args.runs > 1 and current_energy_cv_pct > stability_threshold

    if not baseline_path.exists() or not baseline_path.is_file():
        print(f"Baseline file not found: {baseline_path}")
        return 1

    baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline = baseline_data.get("baseline", {})

    baseline_stats = baseline_data.get("statistics", {})
    baseline_energy = float(
        baseline_stats.get(
            "estimated_energy_wh_median",
            baseline.get("estimated_energy_wh", 0.0),
        )
    )
    current_energy = float(current_summary.estimated_energy_wh_median)

    if baseline_energy <= 0:
        increase_pct = 0.0
    else:
        increase_pct = ((current_energy - baseline_energy) / baseline_energy) * 100.0

    threshold_pct = args.energy_threshold_pct
    if threshold_pct is None:
        threshold_pct = config.baseline_energy_threshold_pct

    regression = increase_pct > threshold_pct
    exit_code = 2 if regression else 0

    response_payload = {
        "baseline_path": str(baseline_path),
        "collector": args.collector,
        "runs": args.runs,
        "threshold_pct": threshold_pct,
        "baseline_energy_wh": baseline_energy,
        "current_energy_wh": current_energy,
        "increase_pct": round(increase_pct, 4),
        "regression": regression,
        "status": "failed" if regression else "passed",
        "current": _result_to_dict(current),
        "current_statistics": {
            "estimated_energy_wh_mean": current_summary.estimated_energy_wh_mean,
            "estimated_energy_wh_median": current_summary.estimated_energy_wh_median,
            "estimated_energy_wh_stddev": current_summary.estimated_energy_wh_stddev,
            "estimated_energy_wh_cv_pct": current_energy_cv_pct,
            "cpu_seconds_median": current_summary.cpu_seconds_median,
            "memory_mb_median": current_summary.memory_mb_median,
        },
        "stability": {
            "max_energy_cv_pct": stability_threshold,
            "unstable": unstable,
        },
    }

    try:
        validate_named_schema("baseline_compare", response_payload)
    except SchemaValidationError as exc:
        print(f"Output schema validation failed: {exc}")
        return 1

    if config.history_enabled and should_save_run(args.save_run, config.history_auto_save):
        write_audit_run(
            project_root=config.project_root,
            history_dir=config.history_dir,
            command_name="baseline-compare",
            payload={"command": "baseline compare", "result": response_payload},
        )

    if args.json:
        print(json.dumps(response_payload, indent=2))
        if args.fail_on_unstable and unstable:
            return 3
        return exit_code

    print("EcoCode baseline comparison")
    print(f"Baseline file:          {baseline_path}")
    print(f"Baseline energy Wh:     {baseline_energy}")
    print(f"Current energy Wh:      {current_energy}")
    print(f"Energy increase (%):    {round(increase_pct, 4)}")
    print(f"Threshold (%):          {threshold_pct}")
    if args.runs > 1:
        print(f"Energy CV (%):          {current_energy_cv_pct}")
        print(f"Stability limit (%):    {stability_threshold}")
        if unstable:
            print("Stability:              UNSTABLE")
            if args.fail_on_unstable:
                return 3

    if regression:
        print("Status:                 FAILED (energy regression detected)")
    else:
        print("Status:                 PASSED")

    return exit_code
