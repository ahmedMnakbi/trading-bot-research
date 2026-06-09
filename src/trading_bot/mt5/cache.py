from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from trading_bot.data.cache import safe_symbol
from trading_bot.mt5.data import Mt5RateBar, build_mt5_quality_report, validate_mt5_bars


def mt5_rates_path(cache_dir: Path, broker: str, symbol: str, timeframe: str) -> Path:
    return cache_dir / broker / safe_symbol(symbol) / f"{timeframe}.parquet"


def mt5_rates_metadata_path(cache_dir: Path, broker: str, symbol: str, timeframe: str) -> Path:
    return cache_dir / broker / safe_symbol(symbol) / f"{timeframe}.metadata.json"


class Mt5RatesCache:
    def __init__(self, cache_dir: str | Path = "data/raw/mt5_rates") -> None:
        self.cache_dir = Path(cache_dir)

    def path_for(self, broker: str, symbol: str, timeframe: str) -> Path:
        return mt5_rates_path(self.cache_dir, broker, symbol, timeframe)

    def metadata_path_for(self, broker: str, symbol: str, timeframe: str) -> Path:
        return mt5_rates_metadata_path(self.cache_dir, broker, symbol, timeframe)

    def read(self, broker: str, symbol: str, timeframe: str) -> list[Mt5RateBar]:
        path = self.path_for(broker, symbol, timeframe)
        if not path.exists():
            return []
        try:
            dataframe = pd.read_parquet(path)
        except Exception as exc:
            raise ValueError(f"corrupted MT5 Parquet cache: {path}") from exc
        return _dataframe_to_bars(dataframe)

    def merge_and_write(
        self,
        broker: str,
        symbol: str,
        timeframe: str,
        bars: list[Mt5RateBar],
        *,
        validate_continuity: bool = True,
    ) -> list[Mt5RateBar]:
        existing = self.read(broker, symbol, timeframe)
        if not bars and existing:
            return existing
        if not bars and not existing:
            raise ValueError("refusing to write empty MT5 rates dataset")
        merged_by_timestamp = {bar.timestamp: bar for bar in [*existing, *bars]}
        merged = [merged_by_timestamp[timestamp] for timestamp in sorted(merged_by_timestamp)]
        validate_mt5_bars(merged, timeframe, validate_continuity=validate_continuity)
        self._write_atomic(broker, symbol, timeframe, merged)
        self._write_metadata_atomic(broker, symbol, timeframe, merged)
        return merged

    def inspect(self, broker: str, symbol: str, timeframe: str) -> dict[str, object]:
        bars = self.read(broker, symbol, timeframe)
        if not bars:
            raise ValueError("no cached MT5 rates found")
        report = build_mt5_quality_report(bars, timeframe)
        return {
            **asdict(report),
            "broker": broker,
            "symbol": symbol,
            "timeframe": timeframe,
            "cache_file_path": str(self.path_for(broker, symbol, timeframe)),
            "metadata_file_path": str(self.metadata_path_for(broker, symbol, timeframe)),
        }

    def _write_atomic(
        self,
        broker: str,
        symbol: str,
        timeframe: str,
        bars: list[Mt5RateBar],
    ) -> None:
        path = self.path_for(broker, symbol, timeframe)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        _bars_to_dataframe(bars).to_parquet(temp_path, index=False)
        os.replace(temp_path, path)

    def _write_metadata_atomic(
        self,
        broker: str,
        symbol: str,
        timeframe: str,
        bars: list[Mt5RateBar],
    ) -> None:
        metadata_path = self.metadata_path_for(broker, symbol, timeframe)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        report = build_mt5_quality_report(bars, timeframe)
        metadata = {
            "broker": broker,
            "symbol": symbol,
            "timeframe": timeframe,
            "first_timestamp": bars[0].timestamp.isoformat(),
            "last_timestamp": bars[-1].timestamp.isoformat(),
            "rows": len(bars),
            "fetched_at": datetime.now(UTC).isoformat(),
            "source": "mt5_readonly_rates",
            "quality": asdict(report),
        }
        temp_path = metadata_path.with_suffix(f"{metadata_path.suffix}.tmp")
        temp_path.write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")
        os.replace(temp_path, metadata_path)


def _bars_to_dataframe(bars: list[Mt5RateBar]) -> pd.DataFrame:
    return pd.DataFrame([bar.model_dump() for bar in bars])


def _dataframe_to_bars(dataframe: pd.DataFrame) -> list[Mt5RateBar]:
    bars: list[Mt5RateBar] = []
    for row in dataframe.to_dict(orient="records"):
        timestamp = _timestamp(row["timestamp"])
        new_york_timestamp = _timestamp(row["new_york_timestamp"])
        bars.append(
            Mt5RateBar(
                timestamp=timestamp,
                new_york_timestamp=new_york_timestamp,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                spread=row.get("spread"),
                real_volume=row.get("real_volume"),
            )
        )
    return bars


def _timestamp(value: object) -> datetime:
    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()
    if not isinstance(value, datetime):
        raise ValueError(f"invalid timestamp value: {value}")
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
