from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class TrendPoint:
    timestamp: str
    command: str
    energy_wh: float


def extract_energy_from_payload(payload: dict) -> float | None:
    result = payload.get("result", {})
    if not isinstance(result, dict):
        return None

    if "estimated_energy_wh" in result:
        return float(result["estimated_energy_wh"])

    if "total_energy_wh" in result:
        return float(result["total_energy_wh"])

    if "current_energy_wh" in result:
        return float(result["current_energy_wh"])

    current = result.get("current")
    if isinstance(current, dict) and "estimated_energy_wh" in current:
        return float(current["estimated_energy_wh"])

    return None


def collect_trend_points(history_dir: Path) -> list[TrendPoint]:
    if not history_dir.exists() or not history_dir.is_dir():
        return []

    points: list[TrendPoint] = []
    for file_path in sorted(history_dir.glob("*.json")):
        raw = json.loads(file_path.read_text(encoding="utf-8"))
        command = str(raw.get("command", "unknown"))
        energy = extract_energy_from_payload(raw)
        if energy is None:
            continue

        stamp = file_path.name.split("_", 1)[0]
        points.append(
            TrendPoint(
                timestamp=stamp,
                command=command,
                energy_wh=energy,
            )
        )

    return points


def summarize_trend(points: list[TrendPoint]) -> dict[str, float | int | None]:
    if not points:
        return {
            "count": 0,
            "first_energy_wh": None,
            "last_energy_wh": None,
            "min_energy_wh": None,
            "max_energy_wh": None,
            "delta_wh": None,
            "delta_pct": None,
        }

    energies = [p.energy_wh for p in points]
    first = energies[0]
    last = energies[-1]
    delta_wh = round(last - first, 6)

    if first == 0:
        delta_pct = None
    else:
        delta_pct = round((delta_wh / first) * 100.0, 4)

    return {
        "count": len(points),
        "first_energy_wh": round(first, 6),
        "last_energy_wh": round(last, 6),
        "min_energy_wh": round(min(energies), 6),
        "max_energy_wh": round(max(energies), 6),
        "delta_wh": delta_wh,
        "delta_pct": delta_pct,
    }
