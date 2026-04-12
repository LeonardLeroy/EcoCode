from __future__ import annotations

from pathlib import Path

from ecocode.cli import main
from ecocode.core.profiler import (
    DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
    ProfileResult,
    _parse_linux_cgroup_relative_path,
    _parse_tasklist_memory_mb,
    _profile_runtime,
    _read_linux_cgroup_memory_peak_mb,
    profile_script,
    profile_script_repeated,
)
from ecocode.core.benchmark import run_benchmark_suite


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


def test_profile_script_forwards_sampling_interval(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    captured = {}

    def fake_runtime(script_path, cpu_energy_factor, memory_energy_factor, sampling_interval_seconds):
        captured["script_path"] = script_path
        captured["sampling_interval_seconds"] = sampling_interval_seconds
        return ProfileResult(
            script=str(script_path),
            cpu_seconds=0.1,
            memory_mb=1.0,
            estimated_energy_wh=0.01,
            sustainability_score=99,
        )

    monkeypatch.setattr("ecocode.core.profiler._profile_runtime", fake_runtime)
    result = profile_script(
        script,
        collector="runtime",
        sampling_interval_seconds=0.015,
    )

    assert result.script == str(script)
    assert captured["script_path"] == script
    assert captured["sampling_interval_seconds"] == 0.015


def test_profile_script_repeated_forwards_sampling_interval(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "demo.py"
    script.write_text("print('ok')\n", encoding="utf-8")

    captured = []

    def fake_profile_script(script_path, collector, cpu_energy_factor, memory_energy_factor, sampling_interval_seconds):
        captured.append(sampling_interval_seconds)
        return ProfileResult(
            script=str(script_path),
            cpu_seconds=0.1,
            memory_mb=1.0,
            estimated_energy_wh=0.01,
            sustainability_score=99,
        )

    monkeypatch.setattr("ecocode.core.profiler.profile_script", fake_profile_script)

    results = profile_script_repeated(
        script,
        collector="runtime",
        runs=2,
        sampling_interval_seconds=0.03,
    )

    assert len(results) == 2
    assert captured == [0.03, 0.03]


def test_benchmark_suite_forwards_sampling_interval(monkeypatch, tmp_path: Path) -> None:
    fixtures_dir = tmp_path / "fixtures"
    fixtures_dir.mkdir()
    (fixtures_dir / "one.py").write_text("print('ok')\n", encoding="utf-8")

    captured = {}

    def fake_profile_script_repeated(script_path, collector, runs, cpu_energy_factor, memory_energy_factor, sampling_interval_seconds):
        captured["sampling_interval_seconds"] = sampling_interval_seconds
        return [
            ProfileResult(
                script=str(script_path),
                cpu_seconds=0.1,
                memory_mb=1.0,
                estimated_energy_wh=0.01,
                sustainability_score=99,
            )
        ]

    monkeypatch.setattr("ecocode.core.benchmark.profile_script_repeated", fake_profile_script_repeated)

    result = run_benchmark_suite(
        fixtures_dir=fixtures_dir,
        collector="runtime",
        runs=1,
        sampling_interval_seconds=DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
        max_files=1,
    )

    assert result.total_fixtures == 1
    assert captured["sampling_interval_seconds"] == DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS


def test_parse_linux_cgroup_relative_path_v2() -> None:
    content = "0::/user.slice/app.slice/test.scope\n"
    assert _parse_linux_cgroup_relative_path(content) == "/user.slice/app.slice/test.scope"


def test_read_linux_cgroup_memory_peak_mb_v2(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    sys_root = tmp_path / "sys" / "fs" / "cgroup"
    pid_dir = proc_root / "4242"
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / "cgroup").write_text("0::/demo.slice\n", encoding="utf-8")

    cgroup_dir = sys_root / "demo.slice"
    cgroup_dir.mkdir(parents=True, exist_ok=True)
    # 8 MiB
    (cgroup_dir / "memory.peak").write_text(str(8 * 1024 * 1024), encoding="utf-8")

    value = _read_linux_cgroup_memory_peak_mb(
        process_id=4242,
        proc_root=proc_root,
        sys_cgroup_root=sys_root,
    )
    assert value == 8.0


def test_read_linux_cgroup_memory_peak_mb_returns_zero_when_missing(tmp_path: Path) -> None:
    proc_root = tmp_path / "proc"
    sys_root = tmp_path / "sys" / "fs" / "cgroup"
    pid_dir = proc_root / "9999"
    pid_dir.mkdir(parents=True, exist_ok=True)
    (pid_dir / "cgroup").write_text("0::/missing.slice\n", encoding="utf-8")

    value = _read_linux_cgroup_memory_peak_mb(
        process_id=9999,
        proc_root=proc_root,
        sys_cgroup_root=sys_root,
    )
    assert value == 0.0
