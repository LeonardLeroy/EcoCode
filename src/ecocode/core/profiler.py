from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ProfileResult:
    script: str
    cpu_seconds: float
    memory_mb: float
    estimated_energy_wh: float
    sustainability_score: int


def profile_script(script_path: Path) -> ProfileResult:
    """Return deterministic fake metrics as a placeholder for real profilers."""
    if not script_path.exists() or not script_path.is_file():
        raise FileNotFoundError(f"Script not found: {script_path}")

    digest = hashlib.sha256(script_path.as_posix().encode("utf-8")).hexdigest()
    base = int(digest[:8], 16)

    cpu_seconds = round(0.5 + (base % 900) / 100.0, 2)
    memory_mb = round(20 + (base % 2000) / 10.0, 2)
    estimated_energy_wh = round(cpu_seconds * 0.07 + memory_mb * 0.003, 4)

    score = max(0, 100 - int(cpu_seconds * 2.2 + memory_mb * 0.08))

    return ProfileResult(
        script=str(script_path),
        cpu_seconds=cpu_seconds,
        memory_mb=memory_mb,
        estimated_energy_wh=estimated_energy_wh,
        sustainability_score=score,
    )
