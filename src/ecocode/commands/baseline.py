from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.config import load_project_config
from ecocode.core.history import should_save_run, write_audit_run
from ecocode.core.profiler import ProfileResult, profile_script


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
    create_parser.set_defaults(handler=handle_create)

    compare_parser = baseline_subparsers.add_parser(
        "compare",
        help="Compare current script profile against a baseline",
    )
    compare_parser.add_argument("script", help="Path to the script to profile")
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

    try:
        result = profile_script(script_path)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "baseline": _result_to_dict(result),
    }
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

    try:
        current = profile_script(script_path)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    if not baseline_path.exists() or not baseline_path.is_file():
        print(f"Baseline file not found: {baseline_path}")
        return 1

    baseline_data = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline = baseline_data.get("baseline", {})

    baseline_energy = float(baseline.get("estimated_energy_wh", 0.0))
    current_energy = float(current.estimated_energy_wh)

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
        "threshold_pct": threshold_pct,
        "baseline_energy_wh": baseline_energy,
        "current_energy_wh": current_energy,
        "increase_pct": round(increase_pct, 4),
        "regression": regression,
        "status": "failed" if regression else "passed",
        "current": _result_to_dict(current),
    }

    if config.history_enabled and should_save_run(args.save_run, config.history_auto_save):
        write_audit_run(
            project_root=config.project_root,
            history_dir=config.history_dir,
            command_name="baseline-compare",
            payload={"command": "baseline compare", "result": response_payload},
        )

    if args.json:
        print(json.dumps(response_payload, indent=2))
        return exit_code

    print("EcoCode baseline comparison")
    print(f"Baseline file:          {baseline_path}")
    print(f"Baseline energy Wh:     {baseline_energy}")
    print(f"Current energy Wh:      {current_energy}")
    print(f"Energy increase (%):    {round(increase_pct, 4)}")
    print(f"Threshold (%):          {threshold_pct}")

    if regression:
        print("Status:                 FAILED (energy regression detected)")
    else:
        print("Status:                 PASSED")

    return exit_code
