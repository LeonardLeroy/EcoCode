from __future__ import annotations

from pathlib import Path

from ecocode.cli import main
from ecocode.core.profiler import ProfileResult, _parse_tasklist_memory_mb, _profile_runtime


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


def test_profile_runtime_collector_with_subprocess_tree(tmp_path: Path, capsys) -> None:
    script = tmp_path / "runtime_tree.py"
    script.write_text(
        """
import subprocess
import sys

subprocess.run([sys.executable, "-c", "for _ in range(300000): pass"], check=True)
print("done")
""".strip()
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["profile", str(script), "--collector", "runtime", "--json"])
    output = capsys.readouterr()

    assert exit_code == 0
    assert '"cpu_seconds"' in output.out


def test_tasklist_memory_parser() -> None:
    line = '"python.exe","1234","Console","1","12,345 K"'
    parsed = _parse_tasklist_memory_mb(line)
    assert parsed is not None
    assert parsed > 12.0


def test_runtime_dispatches_windows_backend(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    expected = ProfileResult(
        script=str(script),
        cpu_seconds=0.12,
        memory_mb=10.0,
        estimated_energy_wh=0.0384,
        sustainability_score=99,
    )

    monkeypatch.setattr("ecocode.core.profiler.platform.system", lambda: "Windows")
    monkeypatch.setattr("ecocode.core.profiler._profile_runtime_windows", lambda *args: expected)

    result = _profile_runtime(script, cpu_energy_factor=0.07, memory_energy_factor=0.003)
    assert result == expected
