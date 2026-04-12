from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import tomllib


@dataclass(slots=True)
class ProjectConfig:
    project_root: Path
    history_enabled: bool = True
    history_auto_save: bool = False
    history_dir: str = ".ecocode/history"
    baseline_energy_threshold_pct: float = 5.0
    profile_repo_max_files: int = 50


def _find_config_file(start_dir: Path) -> Path | None:
    current = start_dir.resolve()
    for candidate_dir in [current, *current.parents]:
        candidate = candidate_dir / "ecocode.toml"
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def load_project_config(start_dir: Path | None = None) -> ProjectConfig:
    root = (start_dir or Path.cwd()).resolve()
    config_file = _find_config_file(root)

    if config_file is None:
        return ProjectConfig(project_root=root)

    raw = tomllib.loads(config_file.read_text(encoding="utf-8"))
    history = raw.get("history", {})
    baseline = raw.get("baseline", {})
    profile_repo = raw.get("profile_repo", {})

    return ProjectConfig(
        project_root=config_file.parent,
        history_enabled=bool(history.get("enabled", True)),
        history_auto_save=bool(history.get("auto_save", False)),
        history_dir=str(history.get("dir", ".ecocode/history")),
        baseline_energy_threshold_pct=float(
            baseline.get("energy_threshold_pct", 5.0)
        ),
        profile_repo_max_files=int(profile_repo.get("max_files", 50)),
    )
