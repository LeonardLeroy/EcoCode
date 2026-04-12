from __future__ import annotations

import json
from pathlib import Path

from ecocode.cli import main


PROFILE_KEYS = {
    "script",
    "collector",
    "runs",
    "cpu_seconds",
    "memory_mb",
    "estimated_energy_wh",
    "sustainability_score",
}


MEASUREMENT_KEYS = {
    "script",
    "cpu_seconds",
    "memory_mb",
    "estimated_energy_wh",
    "sustainability_score",
}


REPO_KEYS = {
    "root",
    "collector",
    "runs",
    "total_files",
    "total_cpu_seconds",
    "total_memory_mb",
    "total_energy_wh",
    "average_sustainability_score",
    "summary",
    "extensions",
    "files",
}


TREND_SUMMARY_KEYS = {
    "count",
    "first_energy_wh",
    "last_energy_wh",
    "min_energy_wh",
    "max_energy_wh",
    "delta_wh",
    "delta_pct",
}


def test_profile_json_contract(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    exit_code = main(["profile", str(script), "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert set(payload.keys()) == PROFILE_KEYS


def test_baseline_compare_json_contract(tmp_path: Path, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    baseline_file = tmp_path / "baseline.json"

    create_exit = main(["baseline", "create", str(script), "-o", str(baseline_file)])
    assert create_exit == 0
    _ = capsys.readouterr()

    compare_exit = main(
        [
            "baseline",
            "compare",
            str(script),
            "--baseline",
            str(baseline_file),
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert compare_exit == 0
    payload = json.loads(output.out)

    expected_keys = {
        "baseline_path",
        "collector",
        "runs",
        "threshold_pct",
        "baseline_energy_wh",
        "current_energy_wh",
        "increase_pct",
        "regression",
        "status",
        "current",
        "current_statistics",
    }
    assert set(payload.keys()) == expected_keys
    assert set(payload["current"].keys()) == MEASUREMENT_KEYS


def test_profile_repo_json_contract(tmp_path: Path, capsys) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")

    exit_code = main(
        [
            "profile-repo",
            "--root",
            str(tmp_path),
            "--ext",
            ".py",
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert set(payload.keys()) == REPO_KEYS

    assert isinstance(payload["files"], list)
    if payload["files"]:
        assert set(payload["files"][0].keys()) == MEASUREMENT_KEYS


def test_trend_json_contract(tmp_path: Path, monkeypatch, capsys) -> None:
    history = tmp_path / ".ecocode" / "history"
    history.mkdir(parents=True, exist_ok=True)
    (history / "20260412T100000000000Z_profile.json").write_text(
        json.dumps(
            {
                "command": "profile",
                "result": {"estimated_energy_wh": 1.0},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    exit_code = main(["trend", "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert set(payload.keys()) == {"history_dir", "summary", "points"}
    assert set(payload["summary"].keys()) == TREND_SUMMARY_KEYS
