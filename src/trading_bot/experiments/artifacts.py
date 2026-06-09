from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from trading_bot.reporting.artifacts import _json_safe


def write_campaign_artifacts(
    *, output_dir: str | Path, config_snapshot: dict[str, Any], artifacts: dict[str, Any]
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
