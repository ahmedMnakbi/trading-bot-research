from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml


def write_report_artifacts(
    *,
    output_dir: str | Path,
    config_snapshot: dict[str, Any],
    artifacts: dict[str, Any],
) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=False)
    (path / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config_snapshot, sort_keys=False), encoding="utf-8"
    )
    for filename, payload in artifacts.items():
        if filename.endswith(".json"):
            (path / filename).write_text(
                json.dumps(_json_safe(payload), indent=2), encoding="utf-8"
            )
        else:
            (path / filename).write_text(str(payload), encoding="utf-8")
    return path


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Path):
        return os.fspath(value)
    if value == float("inf"):
        return "Infinity"
    return value
