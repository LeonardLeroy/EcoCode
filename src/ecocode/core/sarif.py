from __future__ import annotations

import json
from pathlib import Path


def _score_to_level(score: int) -> str:
    if score < 60:
        return "error"
    if score < 80:
        return "warning"
    return "note"


def build_repo_profile_sarif(payload: dict) -> dict:
    files = payload.get("files", [])

    results = []
    for entry in files:
        script = str(entry.get("script", ""))
        score = int(entry.get("sustainability_score", 0))
        energy = float(entry.get("estimated_energy_wh", 0.0))
        memory = float(entry.get("memory_mb", 0.0))
        cpu = float(entry.get("cpu_seconds", 0.0))

        results.append(
            {
                "ruleId": "ecocode.energy.profile",
                "level": _score_to_level(score),
                "message": {
                    "text": (
                        f"Energy={energy}Wh CPU={cpu}s Memory={memory}MB "
                        f"Score={score}/100"
                    )
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": script,
                            }
                        }
                    }
                ],
            }
        )

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "EcoCode",
                        "informationUri": "https://github.com/LeonardLeroy/EcoCode",
                        "rules": [
                            {
                                "id": "ecocode.energy.profile",
                                "name": "Energy profile result",
                                "shortDescription": {
                                    "text": "Per-file energy profile summary"
                                },
                            }
                        ],
                    }
                },
                "results": results,
                "properties": {
                    "root": payload.get("root"),
                    "total_files": payload.get("total_files"),
                    "total_energy_wh": payload.get("total_energy_wh"),
                    "average_sustainability_score": payload.get(
                        "average_sustainability_score"
                    ),
                },
            }
        ],
    }


def write_sarif_output(sarif_payload: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sarif_payload, indent=2), encoding="utf-8")
    return output_path
