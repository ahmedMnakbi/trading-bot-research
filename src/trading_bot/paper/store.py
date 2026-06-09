from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from trading_bot.paper.state import PaperState
from trading_bot.portfolio.portfolio_state import PortfolioPaperState


class PaperStateStore:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)

    def run_dir(self, paper_run_id: str) -> Path:
        return self.state_dir / paper_run_id

    def save(self, state: PaperState, metadata: dict[str, Any]) -> None:
        run_dir = self.run_dir(state.paper_run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        state_path = run_dir / "state.json"
        tmp_path = state_path.with_suffix(".json.tmp")
        tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp_path, state_path)
        pd.DataFrame(state.orders).to_parquet(run_dir / "orders.parquet", index=False)
        pd.DataFrame(state.trades).to_parquet(run_dir / "trades.parquet", index=False)
        pd.DataFrame(state.equity_curve).to_parquet(run_dir / "equity_curve.parquet", index=False)
        (run_dir / "run_metadata.json").write_text(
            json.dumps(_json_safe(metadata), indent=2), encoding="utf-8"
        )

    def load(self, paper_run_id: str) -> PaperState:
        path = self.run_dir(paper_run_id) / "state.json"
        if not path.exists():
            raise ValueError(f"missing paper state: {path}")
        try:
            return PaperState.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"corrupted paper state: {path}") from exc

    def latest_state(
        self, *, exchange: str, symbol: str, timeframe: str, strategy: str
    ) -> PaperState | None:
        if not self.state_dir.exists():
            return None
        for path in sorted(self.state_dir.glob("*/state.json"), reverse=True):
            try:
                state = PaperState.model_validate_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if (
                state.exchange == exchange
                and state.symbol == symbol
                and state.timeframe == timeframe
                and state.strategy == strategy
            ):
                return state
        return None


class PortfolioPaperStateStore:
    def __init__(self, state_dir: str | Path) -> None:
        self.state_dir = Path(state_dir)

    def run_dir(self, portfolio_paper_run_id: str) -> Path:
        return self.state_dir / portfolio_paper_run_id

    def save(self, state: PortfolioPaperState, metadata: dict[str, Any]) -> None:
        run_dir = self.run_dir(state.portfolio_paper_run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        state_path = run_dir / "state.json"
        tmp_path = state_path.with_suffix(".json.tmp")
        tmp_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp_path, state_path)
        _records_frame(state.orders).to_parquet(run_dir / "orders.parquet", index=False)
        _records_frame(state.trades).to_parquet(run_dir / "trades.parquet", index=False)
        _records_frame(state.equity_curve).to_parquet(run_dir / "equity_curve.parquet", index=False)
        _records_frame(state.exposure_snapshots).to_parquet(
            run_dir / "exposure_snapshots.parquet", index=False
        )
        (run_dir / "run_metadata.json").write_text(
            json.dumps(_json_safe(metadata), indent=2), encoding="utf-8"
        )

    def load(self, portfolio_paper_run_id: str) -> PortfolioPaperState:
        path = self.run_dir(portfolio_paper_run_id) / "state.json"
        if not path.exists():
            raise ValueError(f"missing portfolio paper state: {path}")
        try:
            return PortfolioPaperState.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"corrupted portfolio paper state: {path}") from exc

    def latest_state(
        self,
        *,
        exchange: str,
        symbols: list[str],
        timeframe: str,
        strategy_map: dict[str, str],
    ) -> PortfolioPaperState | None:
        if not self.state_dir.exists():
            return None
        for path in sorted(self.state_dir.glob("*/state.json"), reverse=True):
            try:
                state = PortfolioPaperState.model_validate_json(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if (
                state.exchange == exchange
                and state.symbols == symbols
                and state.timeframe == timeframe
                and state.strategy_map == strategy_map
            ):
                return state
        return None


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(_json_safe(payload)) + "\n")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Path):
        return os.fspath(value)
    return value


def _records_frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([_parquet_safe(record) for record in records])


def _parquet_safe(value: Any) -> Any:
    if isinstance(value, dict):
        safe = {key: _parquet_safe(nested) for key, nested in value.items()}
        if any(isinstance(nested, (dict, list)) for nested in safe.values()):
            return json.dumps(safe)
        return safe
    if isinstance(value, list):
        return json.dumps(_json_safe(value))
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Path):
        return os.fspath(value)
    return value
