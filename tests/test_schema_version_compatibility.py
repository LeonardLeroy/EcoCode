from __future__ import annotations

import json
from pathlib import Path

from ecocode.cli import main


def test_profile_json_includes_schema_version(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    exit_code = main(["profile", str(script), "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["schemaVersion"] == 1


def test_baseline_compare_accepts_legacy_baseline_without_schema_version(
    tmp_path: Path,
    capsys,
) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    legacy_baseline = tmp_path / "legacy-baseline.json"
    legacy_baseline.write_text(
        json.dumps(
            {
                "version": 1,
                "baseline": {"estimated_energy_wh": 0.0001},
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "baseline",
            "compare",
            str(script),
            "--baseline",
            str(legacy_baseline),
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert exit_code in {0, 2}
    payload = json.loads(output.out)
    assert payload["schemaVersion"] == 1
