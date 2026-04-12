from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Literal

from ecocode.core.profiler import CollectorType, profile_script_repeated, summarize_profile_runs
from ecocode.core.repository_profiler import discover_profile_targets


NoiseProfile = Literal["idle", "warm", "cpu-bound"]


@dataclass(frozen=True, slots=True)
class BenchmarkNoiseDefaults:
    runs: int
    max_energy_cv_pct: float
    max_suite_cv_pct: float
    max_unstable_fixtures: int


NOISE_PROFILE_DEFAULTS: dict[NoiseProfile, BenchmarkNoiseDefaults] = {
    "idle": BenchmarkNoiseDefaults(
        runs=5,
        max_energy_cv_pct=20.0,
        max_suite_cv_pct=12.0,
        max_unstable_fixtures=0,
    ),
    "warm": BenchmarkNoiseDefaults(
        runs=7,
        max_energy_cv_pct=15.0,
        max_suite_cv_pct=10.0,
        max_unstable_fixtures=0,
    ),
    "cpu-bound": BenchmarkNoiseDefaults(
        runs=9,
        max_energy_cv_pct=10.0,
        max_suite_cv_pct=7.0,
        max_unstable_fixtures=0,
    ),
}


@dataclass(slots=True)
class BenchmarkFixtureResult:
    script: str
    runs: int
    energy_wh_mean: float
    energy_wh_median: float
    energy_wh_stddev: float
    energy_wh_cv_pct: float
    unstable: bool


@dataclass(slots=True)
class BenchmarkSuiteResult:
    fixtures_dir: str
    collector: CollectorType
    noise_profile: NoiseProfile
    runs: int
    max_energy_cv_pct: float
    max_suite_cv_pct: float
    max_unstable_fixtures: int
    total_fixtures: int
    unstable_fixtures: int
    acceptance_passed: bool
    summary_energy_wh_mean: float
    summary_energy_wh_median: float
    summary_energy_wh_stddev: float
    summary_energy_wh_cv_pct: float
    fixtures: list[BenchmarkFixtureResult]


def discover_benchmark_fixtures(fixtures_dir: Path, max_files: int = 50) -> list[Path]:
    if not fixtures_dir.exists() or not fixtures_dir.is_dir():
        raise FileNotFoundError(f"Benchmark fixtures directory not found: {fixtures_dir}")

    return discover_profile_targets(
        root=fixtures_dir,
        extensions={".py"},
        max_files=max_files,
        include_globs=["**/*.py", "*.py"],
    )


def run_benchmark_suite(
    fixtures_dir: Path,
    collector: CollectorType = "placeholder",
    noise_profile: NoiseProfile = "warm",
    runs: int | None = None,
    max_energy_cv_pct: float | None = None,
    max_suite_cv_pct: float | None = None,
    max_unstable_fixtures: int | None = None,
    max_files: int = 50,
    cpu_energy_factor: float = 0.07,
    memory_energy_factor: float = 0.003,
    sampling_interval_seconds: float = 0.02,
) -> BenchmarkSuiteResult:
    defaults = NOISE_PROFILE_DEFAULTS[noise_profile]
    resolved_runs = runs if runs is not None else defaults.runs
    resolved_max_energy_cv_pct = (
        max_energy_cv_pct
        if max_energy_cv_pct is not None
        else defaults.max_energy_cv_pct
    )
    resolved_max_suite_cv_pct = (
        max_suite_cv_pct
        if max_suite_cv_pct is not None
        else defaults.max_suite_cv_pct
    )
    resolved_max_unstable_fixtures = (
        max_unstable_fixtures
        if max_unstable_fixtures is not None
        else defaults.max_unstable_fixtures
    )

    if resolved_runs <= 0:
        raise ValueError("runs must be greater than 0")
    if max_files <= 0:
        raise ValueError("max_files must be greater than 0")
    if resolved_max_energy_cv_pct < 0:
        raise ValueError("max_energy_cv_pct must be greater than or equal to 0")
    if resolved_max_suite_cv_pct < 0:
        raise ValueError("max_suite_cv_pct must be greater than or equal to 0")
    if resolved_max_unstable_fixtures < 0:
        raise ValueError("max_unstable_fixtures must be greater than or equal to 0")

    fixtures = discover_benchmark_fixtures(fixtures_dir, max_files=max_files)
    if not fixtures:
        raise RuntimeError(f"No Python fixtures found in: {fixtures_dir}")

    fixture_results: list[BenchmarkFixtureResult] = []

    for fixture in fixtures:
        run_results = profile_script_repeated(
            fixture,
            collector=collector,
            runs=resolved_runs,
            cpu_energy_factor=cpu_energy_factor,
            memory_energy_factor=memory_energy_factor,
            sampling_interval_seconds=sampling_interval_seconds,
        )
        stats = summarize_profile_runs(run_results)

        energy_cv_pct = 0.0
        if stats.estimated_energy_wh_mean > 0:
            energy_cv_pct = round(
                (stats.estimated_energy_wh_stddev / stats.estimated_energy_wh_mean) * 100.0,
                6,
            )

        fixture_results.append(
            BenchmarkFixtureResult(
                script=str(fixture),
                runs=resolved_runs,
                energy_wh_mean=stats.estimated_energy_wh_mean,
                energy_wh_median=stats.estimated_energy_wh_median,
                energy_wh_stddev=stats.estimated_energy_wh_stddev,
                energy_wh_cv_pct=energy_cv_pct,
                unstable=energy_cv_pct > resolved_max_energy_cv_pct,
            )
        )

    median_energy_values = [item.energy_wh_median for item in fixture_results]
    summary_mean = round(mean(median_energy_values), 6)
    summary_stddev = round(pstdev(median_energy_values), 6) if len(median_energy_values) > 1 else 0.0
    summary_cv_pct = 0.0
    if summary_mean > 0:
        summary_cv_pct = round((summary_stddev / summary_mean) * 100.0, 6)

    unstable_fixtures = sum(1 for item in fixture_results if item.unstable)
    acceptance_passed = (
        unstable_fixtures <= resolved_max_unstable_fixtures
        and summary_cv_pct <= resolved_max_suite_cv_pct
    )

    return BenchmarkSuiteResult(
        fixtures_dir=str(fixtures_dir),
        collector=collector,
        noise_profile=noise_profile,
        runs=resolved_runs,
        max_energy_cv_pct=resolved_max_energy_cv_pct,
        max_suite_cv_pct=resolved_max_suite_cv_pct,
        max_unstable_fixtures=resolved_max_unstable_fixtures,
        total_fixtures=len(fixture_results),
        unstable_fixtures=unstable_fixtures,
        acceptance_passed=acceptance_passed,
        summary_energy_wh_mean=summary_mean,
        summary_energy_wh_median=round(median(median_energy_values), 6),
        summary_energy_wh_stddev=summary_stddev,
        summary_energy_wh_cv_pct=summary_cv_pct,
        fixtures=fixture_results,
    )
