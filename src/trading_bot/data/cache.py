from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from trading_bot.data.models import OhlcvCandle
from trading_bot.data.validation import sort_and_deduplicate


def safe_symbol(symbol: str) -> str:
    return symbol.replace("/", "_").replace(":", "_")


def cache_file_path(cache_dir: Path, exchange: str, symbol: str, timeframe: str) -> Path:
    return cache_dir / exchange / safe_symbol(symbol) / f"{timeframe}.parquet"


def metadata_file_path(cache_dir: Path, exchange: str, symbol: str, timeframe: str) -> Path:
    return cache_dir / exchange / safe_symbol(symbol) / f"{timeframe}.metadata.json"


def candles_to_dataframe(candles: list[OhlcvCandle]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in candles
        ]
    )


def dataframe_to_candles(dataframe: pd.DataFrame) -> list[OhlcvCandle]:
    candles: list[OhlcvCandle] = []
    for row in dataframe.to_dict(orient="records"):
        timestamp = row["timestamp"]
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.to_pydatetime()
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)
        candles.append(
            OhlcvCandle(
                timestamp=timestamp,
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
            )
        )
    return candles


class OhlcvCache:
    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)

    def path_for(self, exchange: str, symbol: str, timeframe: str) -> Path:
        return cache_file_path(self.cache_dir, exchange, symbol, timeframe)

    def metadata_path_for(self, exchange: str, symbol: str, timeframe: str) -> Path:
        return metadata_file_path(self.cache_dir, exchange, symbol, timeframe)

    def read(self, exchange: str, symbol: str, timeframe: str) -> list[OhlcvCandle]:
        path = self.path_for(exchange, symbol, timeframe)
        if not path.exists():
            return []
        try:
            return dataframe_to_candles(pd.read_parquet(path))
        except Exception as exc:
            raise ValueError(f"corrupted Parquet cache: {path}") from exc

    def merge_and_write(
        self, exchange: str, symbol: str, timeframe: str, candles: list[OhlcvCandle]
    ) -> list[OhlcvCandle]:
        existing = self.read(exchange, symbol, timeframe)
        if not candles and existing:
            return existing
        if not candles and not existing:
            raise ValueError("refusing to write empty OHLCV dataset")

        merged = sort_and_deduplicate([*existing, *candles])
        self._write_atomic(exchange, symbol, timeframe, merged)
        self._write_metadata_atomic(exchange, symbol, timeframe, merged)
        return merged

    def _write_atomic(
        self, exchange: str, symbol: str, timeframe: str, candles: list[OhlcvCandle]
    ) -> None:
        path = self.path_for(exchange, symbol, timeframe)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(f"{path.suffix}.tmp")
        candles_to_dataframe(candles).to_parquet(temp_path, index=False)
        os.replace(temp_path, path)

    def _write_metadata_atomic(
        self, exchange: str, symbol: str, timeframe: str, candles: list[OhlcvCandle]
    ) -> None:
        metadata_path = self.metadata_path_for(exchange, symbol, timeframe)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "exchange": exchange,
            "symbol": symbol,
            "timeframe": timeframe,
            "first_timestamp": candles[0].timestamp.isoformat(),
            "last_timestamp": candles[-1].timestamp.isoformat(),
            "rows": len(candles),
            "fetched_at": datetime.now(UTC).isoformat(),
            "source": "ccxt_public_ohlcv",
        }
        temp_path = metadata_path.with_suffix(f"{metadata_path.suffix}.tmp")
        temp_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        os.replace(temp_path, metadata_path)

