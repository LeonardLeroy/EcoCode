from __future__ import annotations

import json
from pathlib import Path

from ecocode.cli import main


def test_trend_json_summary(tmp_path: Path, monkeypatch, capsys) -> None:
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
    (history / "20260412T110000000000Z_profile-repo.json").write_text(
        json.dumps(
            {
                "command": "profile-repo",
                "result": {"total_energy_wh": 1.25},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    exit_code = main(["trend", "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["summary"]["count"] == 2
    assert payload["summary"]["delta_wh"] == 0.25


def test_trend_filter_by_command_and_limit(tmp_path: Path, monkeypatch, capsys) -> None:
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
    (history / "20260412T110000000000Z_profile.json").write_text(
        json.dumps(
            {
                "command": "profile",
                "result": {"estimated_energy_wh": 0.9},
            }
        ),
        encoding="utf-8",
    )
    (history / "20260412T120000000000Z_profile-repo.json").write_text(
        json.dumps(
            {
                "command": "profile-repo",
                "result": {"total_energy_wh": 1.1},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    exit_code = main(["trend", "--command", "profile", "--limit", "1", "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    payload = json.loads(output.out)
    assert payload["summary"]["count"] == 1
    assert payload["points"][0]["command"] == "profile"
    assert payload["points"][0]["energy_wh"] == 0.9


def test_trend_invalid_limit(capsys) -> None:
    exit_code = main(["trend", "--limit", "0"])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "--limit must be greater than 0" in output.out


def test_trend_writes_csv(tmp_path: Path, monkeypatch, capsys) -> None:
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

    csv_output = tmp_path / "reports" / "trend.csv"
    monkeypatch.chdir(tmp_path)
    exit_code = main(["trend", "--csv-output", str(csv_output)])
    output = capsys.readouterr()

    assert exit_code == 0
    assert csv_output.exists()
    assert "CSV written:" in output.out

    csv_content = csv_output.read_text(encoding="utf-8")
    assert "timestamp,command,energy_wh" in csv_content
    assert "profile,1.0" in csv_content
