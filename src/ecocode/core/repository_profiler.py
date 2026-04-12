from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecocode.core.profiler import CollectorType, ProfileResult, profile_script

DEFAULT_SCRIPT_EXTENSIONS = {
    ".py",
    ".sh",
    ".js",
    ".ts",
    ".rb",
    ".go",
    ".rs",
    ".java",
    ".cs",
    ".c",
    ".cpp",
}

SKIP_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    "bin",
    "obj",
    "__pycache__",
}


@dataclass(slots=True)
class RepoProfileResult:
    root: str
    total_files: int
    total_cpu_seconds: float
    total_memory_mb: float
    total_energy_wh: float
    average_sustainability_score: float
    results: list[ProfileResult]


def discover_profile_targets(
    root: Path,
    extensions: set[str],
    max_files: int,
) -> list[Path]:
    targets: list[Path] = []

    for path in sorted(root.rglob("*")):
        if len(targets) >= max_files:
            break

        if path.is_dir():
            continue

        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue

        if path.suffix.lower() in extensions:
            targets.append(path)

    return targets


def profile_repository(
    root: Path,
    extensions: set[str] | None = None,
    max_files: int = 50,
    collector: CollectorType = "placeholder",
    cpu_energy_factor: float = 0.07,
    memory_energy_factor: float = 0.003,
) -> RepoProfileResult:
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"Repository root not found: {root}")

    profile_extensions = extensions or DEFAULT_SCRIPT_EXTENSIONS
    targets = discover_profile_targets(root, profile_extensions, max_files)

    results = [
        profile_script(
            target,
            collector=collector,
            cpu_energy_factor=cpu_energy_factor,
            memory_energy_factor=memory_energy_factor,
        )
        for target in targets
    ]

    total_files = len(results)
    total_cpu_seconds = round(sum(r.cpu_seconds for r in results), 4)
    total_memory_mb = round(sum(r.memory_mb for r in results), 4)
    total_energy_wh = round(sum(r.estimated_energy_wh for r in results), 6)

    if total_files == 0:
        average_sustainability_score = 0.0
    else:
        average_sustainability_score = round(
            sum(r.sustainability_score for r in results) / total_files,
            2,
        )

    return RepoProfileResult(
        root=str(root),
        total_files=total_files,
        total_cpu_seconds=total_cpu_seconds,
        total_memory_mb=total_memory_mb,
        total_energy_wh=total_energy_wh,
        average_sustainability_score=average_sustainability_score,
        results=results,
    )
