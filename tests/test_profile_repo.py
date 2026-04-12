from __future__ import annotations

import json
from pathlib import Path

from ecocode.cli import main


def test_profile_repo_success(tmp_path: Path, capsys) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "b.js").write_text("console.log('b');\n", encoding="utf-8")

    exit_code = main(["profile-repo", "--root", str(tmp_path), "--max-files", "10"])
    output = capsys.readouterr()

    assert exit_code == 0
    assert "EcoCode repository profile" in output.out
    assert "Files profiled:" in output.out


def test_profile_repo_json_with_extension_filter(tmp_path: Path, capsys) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("hello\n", encoding="utf-8")

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

    payload = json.loads(output.out)
    assert exit_code == 0
    assert payload["total_files"] == 1
    assert payload["extensions"] == [".py"]


def test_profile_repo_invalid_max_files(capsys) -> None:
    exit_code = main(["profile-repo", "--max-files", "0"])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "--max-files must be greater than 0" in output.out


def test_profile_repo_writes_sarif(tmp_path: Path, capsys) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    sarif_path = tmp_path / "reports" / "ecocode.sarif"

    exit_code = main(
        [
            "profile-repo",
            "--root",
            str(tmp_path),
            "--ext",
            ".py",
            "--sarif-output",
            str(sarif_path),
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    assert sarif_path.exists()
    assert "SARIF written:" in output.out

    payload = json.loads(sarif_path.read_text(encoding="utf-8"))
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["tool"]["driver"]["name"] == "EcoCode"
