from __future__ import annotations

from pathlib import Path

from ecocode.core.profiler import profile_script
from ecocode.core.repository_profiler import discover_profile_targets, profile_repository


def test_profile_script_is_deterministic_for_same_path(tmp_path: Path) -> None:
    script = tmp_path / "app.py"
    script.write_text("print('x')\n", encoding="utf-8")

    first = profile_script(script)
    second = profile_script(script)

    assert first == second


def test_profile_metric_ranges_are_bounded(tmp_path: Path) -> None:
    script = tmp_path / "bounded.py"
    script.write_text("print('bounded')\n", encoding="utf-8")

    result = profile_script(script)

    assert 0.5 <= result.cpu_seconds <= 9.49
    assert 20.0 <= result.memory_mb <= 219.9
    assert result.estimated_energy_wh >= 0.0
    assert 0 <= result.sustainability_score <= 100


def test_repository_aggregation_matches_sum_of_files(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('b')\n", encoding="utf-8")
    (tmp_path / "c.txt").write_text("noop\n", encoding="utf-8")

    extensions = {".py"}
    targets = discover_profile_targets(tmp_path, extensions=extensions, max_files=50)
    direct = [profile_script(path) for path in targets]

    aggregated = profile_repository(tmp_path, extensions=extensions, max_files=50)

    assert aggregated.total_files == len(direct)
    assert aggregated.total_cpu_seconds == round(sum(x.cpu_seconds for x in direct), 4)
    assert aggregated.total_memory_mb == round(sum(x.memory_mb for x in direct), 4)
    assert aggregated.total_energy_wh == round(sum(x.estimated_energy_wh for x in direct), 6)


def test_repository_discovery_respects_max_files(tmp_path: Path) -> None:
    for index in range(8):
        (tmp_path / f"file_{index}.py").write_text("print('x')\n", encoding="utf-8")

    result = profile_repository(tmp_path, extensions={".py"}, max_files=3)
    assert result.total_files == 3
