from __future__ import annotations

import hashlib
import platform
import resource
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Literal

CollectorType = Literal["placeholder", "runtime"]


@dataclass(slots=True)
class ProfileResult:
    script: str
    cpu_seconds: float
    memory_mb: float
    estimated_energy_wh: float
    sustainability_score: int


@dataclass(slots=True)
class ProfileStatistics:
    runs: int
    cpu_seconds_mean: float
    cpu_seconds_median: float
    cpu_seconds_stddev: float
    memory_mb_mean: float
    memory_mb_median: float
    memory_mb_stddev: float
    estimated_energy_wh_mean: float
    estimated_energy_wh_median: float
    estimated_energy_wh_stddev: float
    sustainability_score_mean: float
    sustainability_score_min: int
    sustainability_score_max: int


def _estimate_energy_wh(cpu_seconds: float, memory_mb: float) -> float:
    return round(cpu_seconds * 0.07 + memory_mb * 0.003, 4)


def _compute_sustainability_score(cpu_seconds: float, memory_mb: float) -> int:
    return max(0, 100 - int(cpu_seconds * 2.2 + memory_mb * 0.08))


def _profile_placeholder(script_path: Path) -> ProfileResult:
    digest = hashlib.sha256(script_path.as_posix().encode("utf-8")).hexdigest()
    base = int(digest[:8], 16)

    cpu_seconds = round(0.5 + (base % 900) / 100.0, 2)
    memory_mb = round(20 + (base % 2000) / 10.0, 2)
    estimated_energy_wh = _estimate_energy_wh(cpu_seconds, memory_mb)
    score = _compute_sustainability_score(cpu_seconds, memory_mb)

    return ProfileResult(
        script=str(script_path),
        cpu_seconds=cpu_seconds,
        memory_mb=memory_mb,
        estimated_energy_wh=estimated_energy_wh,
        sustainability_score=score,
    )


def _build_runtime_command(script_path: Path) -> list[str]:
    if script_path.suffix.lower() == ".py":
        return [sys.executable, str(script_path)]

    if script_path.is_file() and script_path.stat().st_mode & 0o111:
        return [str(script_path)]

    raise ValueError(
        "Runtime collector supports Python scripts or executable files"
    )


def _profile_runtime(script_path: Path) -> ProfileResult:
    system = platform.system().lower()
    if system not in {"linux", "darwin"}:
        raise RuntimeError("Runtime collector currently supports Unix-like systems")

    command = _build_runtime_command(script_path)

    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    ended = time.perf_counter()
    usage_after = resource.getrusage(resource.RUSAGE_CHILDREN)

    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        stdout = (completed.stdout or "").strip()
        details = stderr or stdout or f"exit code {completed.returncode}"
        raise RuntimeError(f"Runtime execution failed: {details}")

    cpu_user = usage_after.ru_utime - usage_before.ru_utime
    cpu_sys = usage_after.ru_stime - usage_before.ru_stime
    cpu_seconds = round(max(0.0, cpu_user + cpu_sys), 4)

    # On Linux/macOS, ru_maxrss is reported in kilobytes.
    maxrss_kb = max(0.0, usage_after.ru_maxrss - usage_before.ru_maxrss)
    memory_mb = round(maxrss_kb / 1024.0, 4)

    if cpu_seconds == 0.0:
        cpu_seconds = round(max(0.0001, ended - started), 4)

    estimated_energy_wh = _estimate_energy_wh(cpu_seconds, memory_mb)
    score = _compute_sustainability_score(cpu_seconds, memory_mb)

    return ProfileResult(
        script=str(script_path),
        cpu_seconds=cpu_seconds,
        memory_mb=memory_mb,
        estimated_energy_wh=estimated_energy_wh,
        sustainability_score=score,
    )


def profile_script(
    script_path: Path,
    collector: CollectorType = "placeholder",
) -> ProfileResult:
    """Profile a script using either placeholder or runtime collection."""
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")

    if collector == "placeholder":
        return _profile_placeholder(script_path)

    if collector == "runtime":
        return _profile_runtime(script_path)

    raise ValueError(f"Unsupported collector: {collector}")


def profile_script_repeated(
    script_path: Path,
    collector: CollectorType = "placeholder",
    runs: int = 1,
) -> list[ProfileResult]:
    if runs <= 0:
        raise ValueError("runs must be greater than 0")

    return [profile_script(script_path, collector=collector) for _ in range(runs)]


def summarize_profile_runs(results: list[ProfileResult]) -> ProfileStatistics:
    if not results:
        raise ValueError("results must not be empty")

    cpu_values = [result.cpu_seconds for result in results]
    memory_values = [result.memory_mb for result in results]
    energy_values = [result.estimated_energy_wh for result in results]
    score_values = [result.sustainability_score for result in results]

    def _stddev(values: list[float]) -> float:
        if len(values) <= 1:
            return 0.0
        return round(pstdev(values), 6)

    return ProfileStatistics(
        runs=len(results),
        cpu_seconds_mean=round(mean(cpu_values), 6),
        cpu_seconds_median=round(median(cpu_values), 6),
        cpu_seconds_stddev=_stddev(cpu_values),
        memory_mb_mean=round(mean(memory_values), 6),
        memory_mb_median=round(median(memory_values), 6),
        memory_mb_stddev=_stddev(memory_values),
        estimated_energy_wh_mean=round(mean(energy_values), 6),
        estimated_energy_wh_median=round(median(energy_values), 6),
        estimated_energy_wh_stddev=_stddev(energy_values),
        sustainability_score_mean=round(mean(score_values), 6),
        sustainability_score_min=min(score_values),
        sustainability_score_max=max(score_values),
    )
