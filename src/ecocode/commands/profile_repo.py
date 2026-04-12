from __future__ import annotations

import argparse
import json
from statistics import mean, median, pstdev
from pathlib import Path

from ecocode.core.config import load_project_config
from ecocode.core.history import should_save_run, write_audit_run
from ecocode.core.sarif import build_repo_profile_sarif, write_sarif_output
from ecocode.core.repository_profiler import (
    DEFAULT_SCRIPT_EXTENSIONS,
    profile_repository,
)


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "profile-repo",
        help="Profile supported script files across a repository",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root directory (default: current directory)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum number of files to profile",
    )
    parser.add_argument(
        "--ext",
        action="append",
        default=[],
        help="Extension to include (repeatable), example: --ext .py --ext .js",
    )
    parser.add_argument(
        "--include-glob",
        action="append",
        default=[],
        help="Only include files matching glob pattern (repeatable)",
    )
    parser.add_argument(
        "--exclude-glob",
        action="append",
        default=[],
        help="Exclude files matching glob pattern (repeatable)",
    )
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
        help="Repeat repository profiling multiple times and summarize totals",
    )
    parser.add_argument(
        "--max-energy-cv-pct",
        type=float,
        default=None,
        help="Maximum allowed coefficient of variation (%%) for total energy over runs",
    )
    parser.add_argument(
        "--fail-on-unstable",
        action="store_true",
        help="Return non-zero if run variability exceeds stability threshold",
    )
    parser.add_argument(
        "--sarif-output",
        default=None,
        help="Write SARIF report to the given file path",
    )
    parser.add_argument(
        "--save-run",
        action="store_true",
        help="Save this audit result to the local history directory",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    root = Path(args.root).resolve()
    config = load_project_config(Path.cwd())

    max_files = args.max_files
    if max_files is None:
        max_files = config.profile_repo_max_files

    if max_files <= 0:
        print("--max-files must be greater than 0")
        return 1
    if args.runs <= 0:
        print("--runs must be greater than 0")
        return 1

    extensions = {
        ext if ext.startswith(".") else f".{ext}"
        for ext in args.ext
    }
    if not extensions:
        extensions = set(DEFAULT_SCRIPT_EXTENSIONS)

    try:
        run_results = [
            profile_repository(
                root=root,
                extensions=extensions,
                max_files=max_files,
                collector=args.collector,
                cpu_energy_factor=config.calibration_cpu_wh_per_cpu_second,
                memory_energy_factor=config.calibration_memory_wh_per_mb,
                include_globs=args.include_glob,
                exclude_globs=args.exclude_glob,
            )
            for _ in range(args.runs)
        ]
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    result = run_results[-1]

    total_energy_values = [item.total_energy_wh for item in run_results]
    total_energy_cv_pct = 0.0
    energy_mean = mean(total_energy_values)
    energy_stddev = pstdev(total_energy_values) if len(total_energy_values) > 1 else 0.0
    if energy_mean > 0:
        total_energy_cv_pct = round((energy_stddev / energy_mean) * 100.0, 6)

    stability_threshold = args.max_energy_cv_pct
    if stability_threshold is None:
        stability_threshold = config.stability_max_energy_cv_pct
    if stability_threshold < 0:
        print("--max-energy-cv-pct must be greater than or equal to 0")
        return 1
    unstable = args.runs > 1 and total_energy_cv_pct > stability_threshold

    summary = {
        "runs": args.runs,
        "total_energy_wh_mean": round(energy_mean, 6),
        "total_energy_wh_median": round(median(total_energy_values), 6),
        "total_energy_wh_stddev": round(energy_stddev, 6),
        "total_energy_wh_cv_pct": total_energy_cv_pct,
    }

    payload = {
        "root": result.root,
        "collector": args.collector,
        "runs": args.runs,
        "total_files": result.total_files,
        "total_cpu_seconds": result.total_cpu_seconds,
        "total_memory_mb": result.total_memory_mb,
        "total_energy_wh": result.total_energy_wh,
        "average_sustainability_score": result.average_sustainability_score,
        "summary": summary,
        "stability": {
            "max_energy_cv_pct": stability_threshold,
            "unstable": unstable,
        },
        "extensions": sorted(extensions),
        "include_globs": args.include_glob,
        "exclude_globs": args.exclude_glob,
        "files": [
            {
                "script": entry.script,
                "cpu_seconds": entry.cpu_seconds,
                "memory_mb": entry.memory_mb,
                "estimated_energy_wh": entry.estimated_energy_wh,
                "sustainability_score": entry.sustainability_score,
            }
            for entry in result.results
        ],
    }

    if config.history_enabled and should_save_run(args.save_run, config.history_auto_save):
        write_audit_run(
            project_root=config.project_root,
            history_dir=config.history_dir,
            command_name="profile-repo",
            payload={"command": "profile-repo", "result": payload},
        )

    sarif_written_path: Path | None = None
    if args.sarif_output:
        sarif_payload = build_repo_profile_sarif(payload)
        sarif_output_path = Path(args.sarif_output)
        if not sarif_output_path.is_absolute():
            sarif_output_path = (Path.cwd() / sarif_output_path).resolve()
        sarif_written_path = write_sarif_output(sarif_payload, sarif_output_path)

    if args.json:
        print(json.dumps(payload, indent=2))
        if args.fail_on_unstable and unstable:
            return 3
        return 0

    print("EcoCode repository profile")
    print(f"Root:                     {result.root}")
    print(f"Files profiled:           {result.total_files}")
    print(f"Total CPU time (s):       {result.total_cpu_seconds}")
    print(f"Total memory peak (MB):   {result.total_memory_mb}")
    print(f"Total estimated Wh:       {result.total_energy_wh}")
    print(f"Average sustainability:   {result.average_sustainability_score}/100")
    if args.runs > 1:
        print(f"Runs:                     {args.runs}")
        print(f"Energy median (Wh):       {summary['total_energy_wh_median']}")
        print(f"Energy stddev (Wh):       {summary['total_energy_wh_stddev']}")
        print(f"Energy CV (%):            {summary['total_energy_wh_cv_pct']}")
        print(f"Stability limit (%):      {stability_threshold}")
        if unstable:
            print("Stability:                UNSTABLE")
            if args.fail_on_unstable:
                return 3
    if sarif_written_path is not None:
        print(f"SARIF written:            {sarif_written_path}")

    if result.total_files == 0:
        print("No matching files found. Use --ext to adjust file discovery.")

    return 0
