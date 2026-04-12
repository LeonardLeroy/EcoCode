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
    calibration_cpu_wh_per_cpu_second: float = 0.07
    calibration_memory_wh_per_mb: float = 0.003
    stability_max_energy_cv_pct: float = 35.0
    optimize_enabled: bool = True
    optimize_allowed_patch_rule_ids: tuple[str, ...] = ()
    optimize_default_patch_rule_id: str | None = None
    optimize_max_patch_changes: int = 10
    optimize_llm_enabled: bool = False
    optimize_llm_provider: str = "none"
    optimize_llm_model: str = ""
    optimize_llm_max_suggestions: int = 3
    optimize_llm_timeout_seconds: float = 20.0


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
    calibration = raw.get("calibration", {})
    stability = raw.get("stability", {})
    optimize = raw.get("optimize", {})
    optimize_llm = optimize.get("llm", {})

    allowed_patch_rule_ids = optimize.get("allowed_patch_rule_ids", ())
    if not isinstance(allowed_patch_rule_ids, list):
        allowed_patch_rule_ids = []
    normalized_allowed_patch_rule_ids = tuple(
        str(item).strip()
        for item in allowed_patch_rule_ids
        if str(item).strip()
    )

    default_patch_rule_id = optimize.get("default_patch_rule_id")
    if default_patch_rule_id is not None:
        default_patch_rule_id = str(default_patch_rule_id).strip() or None

    llm_provider = str(optimize_llm.get("provider", "none")).strip().lower()
    llm_model = str(optimize_llm.get("model", "")).strip()

    return ProjectConfig(
        project_root=config_file.parent,
        history_enabled=bool(history.get("enabled", True)),
        history_auto_save=bool(history.get("auto_save", False)),
        history_dir=str(history.get("dir", ".ecocode/history")),
        baseline_energy_threshold_pct=float(
            baseline.get("energy_threshold_pct", 5.0)
        ),
        profile_repo_max_files=int(profile_repo.get("max_files", 50)),
        calibration_cpu_wh_per_cpu_second=float(
            calibration.get("cpu_wh_per_cpu_second", 0.07)
        ),
        calibration_memory_wh_per_mb=float(
            calibration.get("memory_wh_per_mb", 0.003)
        ),
        stability_max_energy_cv_pct=float(
            stability.get("max_energy_cv_pct", 35.0)
        ),
        optimize_enabled=bool(optimize.get("enabled", True)),
        optimize_allowed_patch_rule_ids=normalized_allowed_patch_rule_ids,
        optimize_default_patch_rule_id=default_patch_rule_id,
        optimize_max_patch_changes=int(optimize.get("max_patch_changes", 10)),
        optimize_llm_enabled=bool(optimize_llm.get("enabled", False)),
        optimize_llm_provider=llm_provider,
        optimize_llm_model=llm_model,
        optimize_llm_max_suggestions=int(optimize_llm.get("max_suggestions", 3)),
        optimize_llm_timeout_seconds=float(optimize_llm.get("timeout_seconds", 20.0)),
    )
