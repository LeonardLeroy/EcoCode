from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from ecocode.core.config import load_project_config
from ecocode.core.schemas import (
    CURRENT_SCHEMA_VERSION,
    SchemaValidationError,
    validate_named_schema,
)
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
    parser.add_argument(
        "--csv-output",
        default=None,
        help="Write trend points to a CSV file",
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

    csv_written_path: Path | None = None
    if args.csv_output:
        csv_path = Path(args.csv_output)
        if not csv_path.is_absolute():
            csv_path = (Path.cwd() / csv_path).resolve()
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=["timestamp", "command", "energy_wh"],
            )
            writer.writeheader()
            for point in points:
                writer.writerow(
                    {
                        "timestamp": point.timestamp,
                        "command": point.command,
                        "energy_wh": point.energy_wh,
                    }
                )
        csv_written_path = csv_path

    if args.json:
        payload = {
            "schemaVersion": CURRENT_SCHEMA_VERSION,
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
        try:
            validate_named_schema("trend_report", payload)
        except SchemaValidationError as exc:
            print(f"Output schema validation failed: {exc}")
            return 1
        print(json.dumps(payload, indent=2))
        return 0

    print("EcoCode trend")
    print(f"History dir:            {history_path}")
    print(f"Data points:            {summary['count']}")

    if summary["count"] == 0:
        print("No audit history points found.")
        if csv_written_path is not None:
            print(f"CSV written:            {csv_written_path}")
        return 0

    print(f"First energy (Wh):      {summary['first_energy_wh']}")
    print(f"Last energy (Wh):       {summary['last_energy_wh']}")
    print(f"Min energy (Wh):        {summary['min_energy_wh']}")
    print(f"Max energy (Wh):        {summary['max_energy_wh']}")
    print(f"Delta (Wh):             {summary['delta_wh']}")
    print(f"Delta (%):              {summary['delta_pct']}")
    if csv_written_path is not None:
        print(f"CSV written:            {csv_written_path}")
    return 0
