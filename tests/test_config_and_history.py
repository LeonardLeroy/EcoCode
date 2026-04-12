from __future__ import annotations

import json
from pathlib import Path

from ecocode.cli import main
from ecocode.core.config import load_project_config


def test_load_project_config_defaults(tmp_path: Path) -> None:
    config = load_project_config(tmp_path)

    assert config.project_root == tmp_path.resolve()
    assert config.history_enabled is True
    assert config.history_auto_save is False
    assert config.baseline_energy_threshold_pct == 5.0
    assert config.profile_repo_max_files == 50


def test_load_project_config_from_toml(tmp_path: Path) -> None:
    (tmp_path / "ecocode.toml").write_text(
        """
[history]
enabled = true
auto_save = true
dir = ".ecocode/audit-history"

[baseline]
energy_threshold_pct = 7.5

[profile_repo]
max_files = 12
""".strip()
        + "\n",
        encoding="utf-8",
    )

    nested = tmp_path / "src"
    nested.mkdir()
    config = load_project_config(nested)

    assert config.project_root == tmp_path.resolve()
    assert config.history_enabled is True
    assert config.history_auto_save is True
    assert config.history_dir == ".ecocode/audit-history"
    assert config.baseline_energy_threshold_pct == 7.5
    assert config.profile_repo_max_files == 12


def test_profile_save_run_creates_history_file(tmp_path: Path, monkeypatch, capsys) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = main(["profile", str(script), "--save-run"])
    output = capsys.readouterr()

    assert exit_code == 0
    assert "Audit run saved:" in output.out

    history_dir = tmp_path / ".ecocode" / "history"
    files = list(history_dir.glob("*.json"))
    assert len(files) == 1

    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["command"] == "profile"
    assert payload["result"]["script"] == str(script.resolve())


def test_baseline_compare_uses_config_threshold(tmp_path: Path, monkeypatch, capsys) -> None:
    (tmp_path / "ecocode.toml").write_text(
        """
[baseline]
energy_threshold_pct = 1000000.0
""".strip()
        + "\n",
        encoding="utf-8",
    )

    script = tmp_path / "demo.py"
    script.write_text("print('hello')\n", encoding="utf-8")

    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(
        json.dumps({"version": 1, "baseline": {"estimated_energy_wh": 0.0001}}),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    exit_code = main(
        [
            "baseline",
            "compare",
            str(script),
            "--baseline",
            str(baseline_file),
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    assert "Threshold (%):          1000000.0" in output.out
