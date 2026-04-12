from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.config import load_project_config
from ecocode.core.history import should_save_run, write_audit_run
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
        "profile",
        help="Profile a script and estimate energy footprint",
    )
    parser.add_argument("script", help="Path to the script to profile")
    parser.add_argument(
        "--collector",
        choices=["placeholder", "runtime"],
        default="placeholder",
        help="Collector backend to use (default: placeholder)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Repeat profiling multiple times and summarize results",
    )
    parser.add_argument(
        "--sampling-interval",
        type=float,
        default=DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
        help="Sampling interval in seconds for runtime collectors",
    )
    parser.add_argument(
        "--max-energy-cv-pct",
        type=float,
        default=None,
        help="Maximum allowed coefficient of variation (%%) for energy over runs",
    )
    parser.add_argument(
        "--fail-on-unstable",
        action="store_true",
        help="Return non-zero if run variability exceeds stability threshold",
    )
    parser.add_argument(
        "--save-run",
        action="store_true",
        help="Save this audit result to the local history directory",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()
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
            sampling_interval_seconds=args.sampling_interval,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    result = results[-1]
    summary = summarize_profile_runs(results)
    energy_cv_pct = 0.0
    if summary.estimated_energy_wh_mean > 0:
        energy_cv_pct = round(
            (summary.estimated_energy_wh_stddev / summary.estimated_energy_wh_mean) * 100.0,
            6,
        )

    stability_threshold = args.max_energy_cv_pct
    if stability_threshold is None:
        stability_threshold = config.stability_max_energy_cv_pct
    if stability_threshold < 0:
        print("--max-energy-cv-pct must be greater than or equal to 0")
        return 1
    unstable = args.runs > 1 and energy_cv_pct > stability_threshold

    payload = {
        "schemaVersion": CURRENT_SCHEMA_VERSION,
        "script": result.script,
        "collector": args.collector,
        "runs": args.runs,
        "cpu_seconds": result.cpu_seconds,
        "memory_mb": result.memory_mb,
        "estimated_energy_wh": result.estimated_energy_wh,
        "sustainability_score": result.sustainability_score,
    }

    if args.runs > 1:
        payload["summary"] = {
            "cpu_seconds_mean": summary.cpu_seconds_mean,
            "cpu_seconds_median": summary.cpu_seconds_median,
            "cpu_seconds_stddev": summary.cpu_seconds_stddev,
            "memory_mb_mean": summary.memory_mb_mean,
            "memory_mb_median": summary.memory_mb_median,
            "memory_mb_stddev": summary.memory_mb_stddev,
            "estimated_energy_wh_mean": summary.estimated_energy_wh_mean,
            "estimated_energy_wh_median": summary.estimated_energy_wh_median,
            "estimated_energy_wh_stddev": summary.estimated_energy_wh_stddev,
            "estimated_energy_wh_cv_pct": energy_cv_pct,
            "sustainability_score_mean": summary.sustainability_score_mean,
            "sustainability_score_min": summary.sustainability_score_min,
            "sustainability_score_max": summary.sustainability_score_max,
        }
        payload["measurements"] = [
            {
                "cpu_seconds": item.cpu_seconds,
                "memory_mb": item.memory_mb,
                "estimated_energy_wh": item.estimated_energy_wh,
                "sustainability_score": item.sustainability_score,
            }
            for item in results
        ]

    try:
        validate_named_schema("profile_report", payload)
    except SchemaValidationError as exc:
        print(f"Output schema validation failed: {exc}")
        return 1

    saved_path: Path | None = None
    if config.history_enabled and should_save_run(args.save_run, config.history_auto_save):
        saved_path = write_audit_run(
            project_root=config.project_root,
            history_dir=config.history_dir,
            command_name="profile",
            payload={"command": "profile", "result": payload},
        )

    if args.json:
        print(json.dumps(payload, indent=2))
        if args.fail_on_unstable and unstable:
            return 3
        return 0

    print("EcoCode profile report")
    print(f"Script:               {result.script}")
    print(f"CPU time (s):         {result.cpu_seconds}")
    print(f"Memory peak (MB):     {result.memory_mb}")
    print(f"Estimated energy Wh:  {result.estimated_energy_wh}")
    print(f"Sustainability score: {result.sustainability_score}/100")
    if args.runs > 1:
        print(f"Runs:                 {args.runs}")
        print(f"Energy median (Wh):   {summary.estimated_energy_wh_median}")
        print(f"Energy stddev (Wh):   {summary.estimated_energy_wh_stddev}")
        print(f"Energy CV (%):        {energy_cv_pct}")
        print(f"Stability limit (%):  {stability_threshold}")
        if unstable:
            print("Stability:            UNSTABLE")
            if args.fail_on_unstable:
                return 3
    if saved_path is not None:
        print(f"Audit run saved:      {saved_path}")
    return 0
