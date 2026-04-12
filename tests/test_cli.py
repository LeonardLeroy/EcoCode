from __future__ import annotations

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
