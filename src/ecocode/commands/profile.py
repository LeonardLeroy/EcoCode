from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.config import load_project_config
from ecocode.core.history import should_save_run, write_audit_run
from ecocode.core.profiler import profile_script


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
        "--save-run",
        action="store_true",
        help="Save this audit result to the local history directory",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()
    config = load_project_config(Path.cwd())

    try:
        result = profile_script(script_path, collector=args.collector)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc))
        return 1

    payload = {
        "script": result.script,
        "cpu_seconds": result.cpu_seconds,
        "memory_mb": result.memory_mb,
        "estimated_energy_wh": result.estimated_energy_wh,
        "sustainability_score": result.sustainability_score,
    }

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
        return 0

    print("EcoCode profile report")
    print(f"Script:               {result.script}")
    print(f"CPU time (s):         {result.cpu_seconds}")
    print(f"Memory peak (MB):     {result.memory_mb}")
    print(f"Estimated energy Wh:  {result.estimated_energy_wh}")
    print(f"Sustainability score: {result.sustainability_score}/100")
    if saved_path is not None:
        print(f"Audit run saved:      {saved_path}")
    return 0
