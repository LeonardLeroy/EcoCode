from __future__ import annotations

from pathlib import Path

from ecocode.cli import main


def test_profile_runtime_collector_json_success(tmp_path: Path, capsys) -> None:
    script = tmp_path / "runtime_demo.py"
    script.write_text("x = sum(range(1000))\nprint(x)\n", encoding="utf-8")

    exit_code = main(["profile", str(script), "--collector", "runtime", "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    assert '"cpu_seconds"' in output.out
    assert '"memory_mb"' in output.out
    assert '"estimated_energy_wh"' in output.out


def test_profile_runtime_collector_handles_script_failure(tmp_path: Path, capsys) -> None:
    script = tmp_path / "runtime_fail.py"
    script.write_text("raise RuntimeError('boom')\n", encoding="utf-8")

    exit_code = main(["profile", str(script), "--collector", "runtime"])
    output = capsys.readouterr()

    assert exit_code == 1
    assert "Runtime execution failed" in output.out


def test_profile_repo_runtime_collector_smoke(tmp_path: Path, capsys) -> None:
    (tmp_path / "one.py").write_text("print('one')\n", encoding="utf-8")
    (tmp_path / "two.py").write_text("print('two')\n", encoding="utf-8")

    exit_code = main(
        [
            "profile-repo",
            "--root",
            str(tmp_path),
            "--ext",
            ".py",
            "--max-files",
            "2",
            "--collector",
            "runtime",
            "--json",
        ]
    )
    output = capsys.readouterr()

    assert exit_code == 0
    assert '"total_files": 2' in output.out
