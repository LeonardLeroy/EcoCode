from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.profiler import profile_script


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "profile",
        help="Profile a script and estimate energy footprint",
    )
    parser.add_argument("script", help="Path to the script to profile")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    script_path = Path(args.script).resolve()

    try:
        result = profile_script(script_path)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "script": result.script,
                    "cpu_seconds": result.cpu_seconds,
                    "memory_mb": result.memory_mb,
                    "estimated_energy_wh": result.estimated_energy_wh,
                    "sustainability_score": result.sustainability_score,
                },
                indent=2,
            )
        )
        return 0

    print("EcoCode profile report")
    print(f"Script:               {result.script}")
    print(f"CPU time (s):         {result.cpu_seconds}")
    print(f"Memory peak (MB):     {result.memory_mb}")
    print(f"Estimated energy Wh:  {result.estimated_energy_wh}")
    print(f"Sustainability score: {result.sustainability_score}/100")
    return 0
