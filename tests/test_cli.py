from __future__ import annotations

import json
from pathlib import Path

from ecocode.cli import main


def test_profile_command_success(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    exit_code = main(["profile", str(script)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "EcoCode profile report" in captured.out
    assert "Sustainability score" in captured.out


def test_profile_command_missing_script(capsys) -> None:
    exit_code = main(["profile", "missing-script.py"])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Script not found" in captured.out


def test_baseline_create_and_compare_pass(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    baseline_file = tmp_path / ".ecocode" / "baseline.json"

    create_exit = main(
        ["baseline", "create", str(script), "-o", str(baseline_file)]
    )
    create_output = capsys.readouterr()

    assert create_exit == 0
    assert baseline_file.exists()
    assert "Baseline created" in create_output.out

    compare_exit = main(
        [
            "baseline",
            "compare",
            str(script),
            "--baseline",
            str(baseline_file),
        ]
    )
    compare_output = capsys.readouterr()

    assert compare_exit == 0
    assert "Status:" in compare_output.out
    assert "PASSED" in compare_output.out


def test_baseline_compare_regression_exit_code(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(
        json.dumps(
            {
                "version": 1,
                "baseline": {
                    "estimated_energy_wh": 0.0001,
                },
            }
        ),
        encoding="utf-8",
    )

    compare_exit = main(
        [
            "baseline",
            "compare",
            str(script),
            "--baseline",
            str(baseline_file),
            "--energy-threshold-pct",
            "5",
        ]
    )
    compare_output = capsys.readouterr()

    assert compare_exit == 2
    assert "FAILED" in compare_output.out
