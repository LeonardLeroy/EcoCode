from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def should_save_run(explicit_flag: bool, auto_save: bool) -> bool:
    return explicit_flag or auto_save


def write_audit_run(
    *,
    project_root: Path,
    history_dir: str,
    command_name: str,
    payload: dict,
) -> Path:
    output_dir = (project_root / history_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    safe_command = command_name.replace(" ", "-")
    output_file = output_dir / f"{stamp}_{safe_command}.json"
    output_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_file
