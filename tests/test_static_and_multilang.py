from __future__ import annotations

from pathlib import Path

import pytest

from ecocode.core.profiler import (
    _build_runtime_command,
    profile_script,
)
from ecocode.core.repository_profiler import discover_profile_targets, profile_repository


def test_static_collector_is_unmeasured_and_deterministic(tmp_path: Path) -> None:
    script = tmp_path / "loopy.py"
    script.write_text("for i in range(10):\n    print(i)\n", encoding="utf-8")

    first = profile_script(script, collector="static")
    second = profile_script(script, collector="static")

    assert first == second
    assert first.measured is False
    assert first.method == "static_estimate"
    assert first.cpu_seconds > 0.0


def test_static_estimate_scales_with_source_size(tmp_path: Path) -> None:
    small = tmp_path / "small.py"
    small.write_text("print('x')\n", encoding="utf-8")
    large = tmp_path / "large.py"
    large.write_text("\n".join(f"value_{i} = {i}" for i in range(200)) + "\n", encoding="utf-8")

    small_result = profile_script(small, collector="static")
    large_result = profile_script(large, collector="static")

    assert large_result.estimated_energy_wh > small_result.estimated_energy_wh


def test_runtime_command_uses_interpreter_when_available(tmp_path: Path, monkeypatch) -> None:
    script = tmp_path / "demo.sh"
    script.write_text("echo hi\n", encoding="utf-8")

    monkeypatch.setattr(
        "ecocode.core.profiler.shutil.which",
        lambda name: "/usr/bin/bash" if name == "bash" else None,
    )

    command = _build_runtime_command(script)
    assert command == ["/usr/bin/bash", str(script)]


def test_runtime_command_raises_actionable_error_when_interpreter_missing(
    tmp_path: Path, monkeypatch
) -> None:
    script = tmp_path / "demo.rb"
    script.write_text("puts 'hi'\n", encoding="utf-8")

    monkeypatch.setattr("ecocode.core.profiler.shutil.which", lambda name: None)

    with pytest.raises(ValueError, match="ruby"):
        _build_runtime_command(script)


def test_runtime_command_rejects_non_executable_source(tmp_path: Path) -> None:
    source = tmp_path / "lib.c"
    source.write_text("int main(void){return 0;}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="static collector"):
        _build_runtime_command(source)


def test_repo_runtime_falls_back_to_static_for_unrunnable_files(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "lib.c").write_text("int main(void){return 0;}\n", encoding="utf-8")

    result = profile_repository(
        tmp_path,
        extensions={".py", ".c"},
        max_files=10,
        collector="runtime",
    )

    by_name = {Path(entry.script).name: entry for entry in result.results}
    assert by_name["lib.c"].measured is False
    assert by_name["lib.c"].method == "static_estimate"
    # The whole scan did not crash and still counts both files.
    assert result.total_files == 2


def test_discovery_prunes_ignored_directories(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('ok')\n", encoding="utf-8")
    heavy = tmp_path / "node_modules" / "dep"
    heavy.mkdir(parents=True)
    (heavy / "ignored.py").write_text("print('skip me')\n", encoding="utf-8")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "hook.py").write_text("print('skip me too')\n", encoding="utf-8")

    targets = discover_profile_targets(tmp_path, extensions={".py"}, max_files=50)
    names = {path.name for path in targets}

    assert names == {"app.py"}
