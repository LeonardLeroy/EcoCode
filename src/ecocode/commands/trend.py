from __future__ import annotations

import argparse
import json
from pathlib import Path

from ecocode.core.config import load_project_config
from ecocode.core.trend import collect_trend_points, summarize_trend


def register(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "trend",
        help="Summarize energy progression from saved audit history",
    )
    parser.add_argument(
        "--history-dir",
        default=None,
        help="Override history directory path",
    )
    parser.add_argument(
        "--command",
        default=None,
        help="Filter by command name (example: profile-repo)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of most recent points",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )
    parser.set_defaults(handler=handle)


def handle(args: argparse.Namespace) -> int:
    config = load_project_config(Path.cwd())
    history_dir = args.history_dir or config.history_dir
    history_path = (config.project_root / history_dir).resolve()

    points = collect_trend_points(history_path)

    if args.command:
        points = [point for point in points if point.command == args.command]

    if args.limit is not None:
        if args.limit <= 0:
            print("--limit must be greater than 0")
            return 1
        points = points[-args.limit :]

    summary = summarize_trend(points)

    if args.json:
        payload = {
            "history_dir": str(history_path),
            "summary": summary,
            "points": [
                {
                    "timestamp": point.timestamp,
                    "command": point.command,
                    "energy_wh": point.energy_wh,
                }
                for point in points
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0

    print("EcoCode trend")
    print(f"History dir:            {history_path}")
    print(f"Data points:            {summary['count']}")

    if summary["count"] == 0:
        print("No audit history points found.")
        return 0

    print(f"First energy (Wh):      {summary['first_energy_wh']}")
    print(f"Last energy (Wh):       {summary['last_energy_wh']}")
    print(f"Min energy (Wh):        {summary['min_energy_wh']}")
    print(f"Max energy (Wh):        {summary['max_energy_wh']}")
    print(f"Delta (Wh):             {summary['delta_wh']}")
    print(f"Delta (%):              {summary['delta_pct']}")
    return 0
