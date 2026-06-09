from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
import yaml


@dataclass(frozen=True)
class BacktestResult:
    run_id: str
    output_dir: Path
    metrics: dict[str, Any]
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    orders: pd.DataFrame
    metadata: dict[str, Any]


def new_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8]


def write_backtest_artifacts(
    *,
    output_root: str | Path,
    run_id: str,
    config_snapshot: dict[str, Any],
    metrics: dict[str, Any],
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    orders: pd.DataFrame,
    metadata: dict[str, Any],
) -> Path:
    output_dir = Path(output_root) / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config_snapshot, sort_keys=False), encoding="utf-8"
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(_json_safe(metrics), indent=2), encoding="utf-8"
    )
    (output_dir / "run_metadata.json").write_text(
        json.dumps(_json_safe(metadata), indent=2), encoding="utf-8"
    )
    equity_curve.to_parquet(output_dir / "equity_curve.parquet", index=False)
    trades.to_parquet(output_dir / "trades.parquet", index=False)
    orders.to_parquet(output_dir / "orders.parquet", index=False)
    return output_dir


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, float) and value == float("inf"):
        return "Infinity"
    if isinstance(value, Path):
        return os.fspath(value)
    return value

