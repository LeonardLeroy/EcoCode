from __future__ import annotations

import csv
import hashlib
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Literal

try:
    import resource
except ImportError:  # pragma: no cover - unavailable on Windows
    resource = None

CollectorType = Literal["placeholder", "runtime"]
DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS = 0.02


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


def _estimate_energy_wh(
    cpu_seconds: float,
    memory_mb: float,
    cpu_energy_factor: float,
    memory_energy_factor: float,
) -> float:
    return round(
        cpu_seconds * cpu_energy_factor + memory_mb * memory_energy_factor,
        4,
    )


def _compute_sustainability_score(cpu_seconds: float, memory_mb: float) -> int:
    return max(0, 100 - int(cpu_seconds * 2.2 + memory_mb * 0.08))


def _profile_placeholder(
    script_path: Path,
    cpu_energy_factor: float,
    memory_energy_factor: float,
) -> ProfileResult:
    digest = hashlib.sha256(script_path.as_posix().encode("utf-8")).hexdigest()
    base = int(digest[:8], 16)

    cpu_seconds = round(0.5 + (base % 900) / 100.0, 2)
    memory_mb = round(20 + (base % 2000) / 10.0, 2)
    estimated_energy_wh = _estimate_energy_wh(
        cpu_seconds,
        memory_mb,
        cpu_energy_factor,
        memory_energy_factor,
    )
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


def _profile_runtime(
    script_path: Path,
    cpu_energy_factor: float,
    memory_energy_factor: float,
    sampling_interval_seconds: float = DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
) -> ProfileResult:
    system = platform.system().lower()
    command = _build_runtime_command(script_path)

    if system == "linux":
        return _profile_runtime_linux_process_group(
            script_path,
            command,
            cpu_energy_factor,
            memory_energy_factor,
            sampling_interval_seconds,
        )

    if system == "windows":
        return _profile_runtime_windows(
            script_path,
            command,
            cpu_energy_factor,
            memory_energy_factor,
            sampling_interval_seconds,
        )

    if system == "darwin":
        return _profile_runtime_children_usage(
            script_path,
            command,
            cpu_energy_factor,
            memory_energy_factor,
            sampling_interval_seconds,
        )

    raise RuntimeError("Runtime collector currently supports Linux, macOS, and Windows")


def _parse_linux_cgroup_relative_path(proc_cgroup_text: str) -> str | None:
    """Extract cgroup relative path from /proc/<pid>/cgroup content."""

    for raw_line in proc_cgroup_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # v2 format: 0::/path
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue

        _, controllers, relative = parts
        if controllers == "":
            return relative

    # v1 fallback: use first available hierarchy path.
    for raw_line in proc_cgroup_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        return parts[2]

    return None


def _read_first_int_from_file(path: Path) -> int | None:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, PermissionError, OSError):
        return None

    if not text:
        return None

    try:
        return int(text)
    except ValueError:
        return None


def _read_linux_cgroup_memory_peak_mb(
    process_id: int,
    proc_root: Path = Path("/proc"),
    sys_cgroup_root: Path = Path("/sys/fs/cgroup"),
) -> float:
    """Read cgroup memory peak/current usage for a process in MB.

    Prefers cgroup v2 `memory.peak`, then `memory.current`. For v1 layouts, falls
    back to `memory.max_usage_in_bytes` or `memory.usage_in_bytes`.
    Returns 0.0 when cgroup data is unavailable.
    """

    proc_cgroup_path = proc_root / str(process_id) / "cgroup"
    try:
        proc_cgroup_text = proc_cgroup_path.read_text(encoding="utf-8")
    except (FileNotFoundError, PermissionError, OSError):
        return 0.0

    relative_path = _parse_linux_cgroup_relative_path(proc_cgroup_text)
    if relative_path is None:
        return 0.0

    normalized_relative = relative_path.lstrip("/")
    candidate_dirs = [
        sys_cgroup_root / normalized_relative,
        sys_cgroup_root / "memory" / normalized_relative,
    ]

    candidate_files = [
        "memory.peak",
        "memory.current",
        "memory.max_usage_in_bytes",
        "memory.usage_in_bytes",
    ]

    for directory in candidate_dirs:
        for filename in candidate_files:
            raw_value = _read_first_int_from_file(directory / filename)
            if raw_value is None:
                continue

            if raw_value < 0:
                continue

            return round(raw_value / (1024.0 * 1024.0), 6)

    return 0.0


def _profile_runtime_children_usage(
    script_path: Path,
    command: list[str],
    cpu_energy_factor: float,
    memory_energy_factor: float,
    sampling_interval_seconds: float = DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
) -> ProfileResult:
    """Fallback runtime collector based on RUSAGE_CHILDREN aggregates."""

    if resource is None:
        raise RuntimeError("RUSAGE runtime collector is unavailable on this platform")
    if sampling_interval_seconds <= 0:
        raise ValueError("sampling_interval_seconds must be greater than 0")

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

    estimated_energy_wh = _estimate_energy_wh(
        cpu_seconds,
        memory_mb,
        cpu_energy_factor,
        memory_energy_factor,
    )
    score = _compute_sustainability_score(cpu_seconds, memory_mb)

    return ProfileResult(
        script=str(script_path),
        cpu_seconds=cpu_seconds,
        memory_mb=memory_mb,
        estimated_energy_wh=estimated_energy_wh,
        sustainability_score=score,
    )


def _parse_tasklist_memory_mb(tasklist_line: str) -> float | None:
    """Parse a tasklist CSV line and return memory in MB if available."""

    try:
        columns = next(csv.reader([tasklist_line]))
    except (csv.Error, StopIteration):
        return None

    columns = [part.strip().strip('"') for part in columns]
    if len(columns) < 5:
        return None

    memory_text = columns[-1].upper().replace("K", "").replace(" ", "")
    memory_text = memory_text.replace(",", "")
    try:
        memory_kb = float(memory_text)
    except ValueError:
        return None

    return round(memory_kb / 1024.0, 6)


def _read_windows_process_memory_mb(process_id: int) -> float:
    """Read process working set from tasklist; returns 0.0 when unavailable."""

    try:
        completed = subprocess.run(
            ["tasklist", "/FI", f"PID eq {process_id}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return 0.0

    if completed.returncode != 0:
        return 0.0

    output = (completed.stdout or "").strip()
    if not output or output.startswith("INFO:"):
        return 0.0

    first_line = output.splitlines()[0]
    parsed = _parse_tasklist_memory_mb(first_line)
    if parsed is None:
        return 0.0
    return parsed


def _profile_runtime_windows(
    script_path: Path,
    command: list[str],
    cpu_energy_factor: float,
    memory_energy_factor: float,
    sampling_interval_seconds: float = DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
) -> ProfileResult:
    """Windows runtime collector preview (single-process working-set sampling)."""

    if sampling_interval_seconds <= 0:
        raise ValueError("sampling_interval_seconds must be greater than 0")

    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise RuntimeError(f"Runtime execution failed: {exc}") from exc

    started = time.perf_counter()
    peak_memory_mb = 0.0

    while process.poll() is None:
        peak_memory_mb = max(peak_memory_mb, _read_windows_process_memory_mb(process.pid))
        time.sleep(sampling_interval_seconds)

    stdout_text, stderr_text = process.communicate()
    ended = time.perf_counter()

    peak_memory_mb = max(peak_memory_mb, _read_windows_process_memory_mb(process.pid))

    if process.returncode != 0:
        stderr = (stderr_text or "").strip()
        stdout = (stdout_text or "").strip()
        details = stderr or stdout or f"exit code {process.returncode}"
        raise RuntimeError(f"Runtime execution failed: {details}")

    cpu_seconds = round(max(0.0001, ended - started), 6)
    memory_mb = round(peak_memory_mb, 6)

    estimated_energy_wh = _estimate_energy_wh(
        cpu_seconds,
        memory_mb,
        cpu_energy_factor,
        memory_energy_factor,
    )
    score = _compute_sustainability_score(cpu_seconds, memory_mb)

    return ProfileResult(
        script=str(script_path),
        cpu_seconds=cpu_seconds,
        memory_mb=memory_mb,
        estimated_energy_wh=estimated_energy_wh,
        sustainability_score=score,
    )


def _parse_proc_stat(proc_stat_line: str) -> tuple[int, int, int] | None:
    """Parse /proc/<pid>/stat and return (pgrp, cpu_ticks, rss_pages)."""
    right_paren = proc_stat_line.rfind(")")
    if right_paren == -1:
        return None

    tail = proc_stat_line[right_paren + 2 :].split()
    if len(tail) < 22:
        return None

    # Field mapping relative to tail (field 3 starts at index 0).
    pgrp = int(tail[2])
    utime = int(tail[11])
    stime = int(tail[12])
    rss_pages = int(tail[21])
    return pgrp, utime + stime, rss_pages


def _read_process_group_totals(process_group_id: int) -> tuple[int, int]:
    total_ticks = 0
    total_rss_pages = 0

    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue

        stat_path = Path("/proc") / entry / "stat"
        try:
            stat_line = stat_path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue

        parsed = _parse_proc_stat(stat_line)
        if parsed is None:
            continue

        pgrp, cpu_ticks, rss_pages = parsed
        if pgrp != process_group_id:
            continue

        total_ticks += cpu_ticks
        total_rss_pages += max(0, rss_pages)

    return total_ticks, total_rss_pages


def _profile_runtime_linux_process_group(
    script_path: Path,
    command: list[str],
    cpu_energy_factor: float,
    memory_energy_factor: float,
    sampling_interval_seconds: float = DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
) -> ProfileResult:
    """Linux runtime collector with process-group sampling (includes subprocess tree)."""
    if sampling_interval_seconds <= 0:
        raise ValueError("sampling_interval_seconds must be greater than 0")
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except OSError as exc:
        raise RuntimeError(f"Runtime execution failed: {exc}") from exc

    process_group_id = os.getpgid(process.pid)
    page_size = os.sysconf("SC_PAGE_SIZE")
    ticks_per_second = os.sysconf("SC_CLK_TCK")

    start_ticks, start_rss_pages = _read_process_group_totals(process_group_id)
    last_observed_ticks = start_ticks
    peak_rss_pages = start_rss_pages
    cgroup_peak_memory_mb = 0.0

    while process.poll() is None:
        current_ticks, current_rss_pages = _read_process_group_totals(process_group_id)
        last_observed_ticks = max(last_observed_ticks, current_ticks)
        peak_rss_pages = max(peak_rss_pages, current_rss_pages)
        cgroup_peak_memory_mb = max(
            cgroup_peak_memory_mb,
            _read_linux_cgroup_memory_peak_mb(process.pid),
        )
        time.sleep(sampling_interval_seconds)

    stdout_text, stderr_text = process.communicate()

    end_ticks, end_rss_pages = _read_process_group_totals(process_group_id)
    last_observed_ticks = max(last_observed_ticks, end_ticks)
    peak_rss_pages = max(peak_rss_pages, end_rss_pages)
    cgroup_peak_memory_mb = max(cgroup_peak_memory_mb, _read_linux_cgroup_memory_peak_mb(process.pid))

    if process.returncode != 0:
        stderr = (stderr_text or "").strip()
        stdout = (stdout_text or "").strip()
        details = stderr or stdout or f"exit code {process.returncode}"
        raise RuntimeError(f"Runtime execution failed: {details}")

    cpu_ticks = max(0, last_observed_ticks - start_ticks)
    cpu_seconds = round(cpu_ticks / ticks_per_second, 6)

    if cpu_seconds == 0.0:
        cpu_seconds = 0.0001

    process_group_memory_mb = round((peak_rss_pages * page_size) / (1024 * 1024), 6)
    memory_mb = max(process_group_memory_mb, cgroup_peak_memory_mb)

    estimated_energy_wh = _estimate_energy_wh(
        cpu_seconds,
        memory_mb,
        cpu_energy_factor,
        memory_energy_factor,
    )
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
    cpu_energy_factor: float = 0.07,
    memory_energy_factor: float = 0.003,
    sampling_interval_seconds: float = DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
) -> ProfileResult:
    """Profile a script using either placeholder or runtime collection."""
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")

    if collector == "placeholder":
        return _profile_placeholder(
            script_path,
            cpu_energy_factor,
            memory_energy_factor,
        )

    if collector == "runtime":
        return _profile_runtime(
            script_path,
            cpu_energy_factor,
            memory_energy_factor,
            sampling_interval_seconds,
        )

    raise ValueError(f"Unsupported collector: {collector}")


def profile_script_repeated(
    script_path: Path,
    collector: CollectorType = "placeholder",
    runs: int = 1,
    cpu_energy_factor: float = 0.07,
    memory_energy_factor: float = 0.003,
    sampling_interval_seconds: float = DEFAULT_RUNTIME_SAMPLING_INTERVAL_SECONDS,
) -> list[ProfileResult]:
    if runs <= 0:
        raise ValueError("runs must be greater than 0")

    return [
        profile_script(
            script_path,
            collector=collector,
            cpu_energy_factor=cpu_energy_factor,
            memory_energy_factor=memory_energy_factor,
            sampling_interval_seconds=sampling_interval_seconds,
        )
        for _ in range(runs)
    ]


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
