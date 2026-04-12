from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.benchmark import run_benchmark_suite
from ecocode.core.config import load_project_config
from ecocode.core.profiler import DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS
from ecocode.core.schemas import (
    CURRENT_SCHEMA_VERSION,
    SchemaValidationError,
    validate_named_schema,
)


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "benchmark",
        help="Run reproducibility benchmark suite from fixture scripts",
    )
    parser.add_argument(
        "--fixtures-dir",
        default="benchmarks/fixtures",
        help="Path to benchmark fixture directory (default: benchmarks/fixtures)",
    )
    parser.add_argument(
        "--noise-profile",
        choices=["idle", "warm", "cpu-bound"],
        default="warm",
        help="Noise profile preset for runs and acceptance defaults",
    )
    parser.add_argument(
        "--collector",
        choices=["placeholder", "runtime"],
        default="placeholder",
        help="Collector backend to use (default: placeholder)",
    )
    parser.add_argument(
        "--sampling-interval",
        type=float,
        default=DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
        help="Sampling interval in seconds for runtime collectors",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=None,
        help="Number of runs per fixture (default depends on --noise-profile)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=50,
        help="Maximum number of fixture scripts to include",
    )
    parser.add_argument(
        "--max-energy-cv-pct",
        type=float,
        default=None,
        help="Maximum allowed energy CV (%%) per fixture (default depends on profile)",
    )
    parser.add_argument(
        "--max-suite-cv-pct",
        type=float,
        default=None,
        help="Maximum allowed suite-level CV (%%) across fixture medians",
    )
    parser.add_argument(
        "--max-unstable-fixtures",
        type=int,
        default=None,
        help="Maximum allowed unstable fixtures before acceptance fails",
    )
    parser.add_argument(
        "--fail-on-unstable",
        action="store_true",
        help="Return non-zero when at least one fixture is unstable",
    )
    parser.add_argument(
        "--fail-on-acceptance",
        action="store_true",
        help="Return non-zero when acceptance thresholds are not met",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    config = load_project_config(Path.cwd())
    threshold = args.max_energy_cv_pct
    if threshold is None and args.noise_profile == "warm":
        threshold = config.stability_max_energy_cv_pct

    fixtures_dir = Path(args.fixtures_dir)
    if not fixtures_dir.is_absolute():
        fixtures_dir = (Path.cwd() / fixtures_dir).resolve()

    try:
        result = run_benchmark_suite(
            fixtures_dir=fixtures_dir,
            collector=args.collector,
            noise_profile=args.noise_profile,
            runs=args.runs,
            max_energy_cv_pct=threshold,
            max_suite_cv_pct=args.max_suite_cv_pct,
            max_unstable_fixtures=args.max_unstable_fixtures,
            max_files=args.max_files,
            cpu_energy_factor=config.calibration_cpu_wh_per_cpu_second,
            memory_energy_factor=config.calibration_memory_wh_per_mb,
            sampling_interval_seconds=args.sampling_interval,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    payload = {
        "schemaVersion": CURRENT_SCHEMA_VERSION,
        "fixtures_dir": result.fixtures_dir,
        "collector": result.collector,
        "noise_profile": result.noise_profile,
        "runs": result.runs,
        "max_energy_cv_pct": result.max_energy_cv_pct,
        "max_suite_cv_pct": result.max_suite_cv_pct,
        "max_unstable_fixtures": result.max_unstable_fixtures,
        "total_fixtures": result.total_fixtures,
        "unstable_fixtures": result.unstable_fixtures,
        "status": "passed" if result.acceptance_passed else "failed",
        "summary": {
            "energy_wh_mean": result.summary_energy_wh_mean,
            "energy_wh_median": result.summary_energy_wh_median,
            "energy_wh_stddev": result.summary_energy_wh_stddev,
            "energy_wh_cv_pct": result.summary_energy_wh_cv_pct,
        },
        "fixtures": [
            {
                "script": item.script,
                "runs": item.runs,
                "energy_wh_mean": item.energy_wh_mean,
                "energy_wh_median": item.energy_wh_median,
                "energy_wh_stddev": item.energy_wh_stddev,
                "energy_wh_cv_pct": item.energy_wh_cv_pct,
                "unstable": item.unstable,
            }
            for item in result.fixtures
        ],
    }

    try:
        validate_named_schema("benchmark_report", payload)
    except SchemaValidationError as exc:
        print(f"Output schema validation failed: {exc}")
        return 1

    if args.json:
        print(json.dumps(payload, indent=2))
        if args.fail_on_unstable and result.unstable_fixtures > 0:
            return 3
        if args.fail_on_acceptance and not result.acceptance_passed:
            return 4
        return 0

    print("EcoCode benchmark reproducibility")
    print(f"Fixtures dir:            {result.fixtures_dir}")
    print(f"Collector:               {result.collector}")
    print(f"Noise profile:           {result.noise_profile}")
    print(f"Runs per fixture:        {result.runs}")
    print(f"Total fixtures:          {result.total_fixtures}")
    print(f"Unstable fixtures:       {result.unstable_fixtures}")
    print(f"Per-fixture CV limit:    {result.max_energy_cv_pct}%")
    print(f"Suite CV limit:          {result.max_suite_cv_pct}%")
    print(f"Max unstable fixtures:   {result.max_unstable_fixtures}")
    print(f"Suite median Wh:         {result.summary_energy_wh_median}")
    print(f"Suite stddev Wh:         {result.summary_energy_wh_stddev}")
    print(f"Suite CV (%):            {result.summary_energy_wh_cv_pct}")
    print(f"Status:                  {'PASSED' if result.acceptance_passed else 'FAILED'}")

    if args.fail_on_unstable and result.unstable_fixtures > 0:
        return 3
    if args.fail_on_acceptance and not result.acceptance_passed:
        return 4

    return 0
