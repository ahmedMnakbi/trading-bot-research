from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd

from trading_bot.data.cache import cache_file_path, metadata_file_path

FIXTURE_EXCHANGE = "kraken"
FIXTURE_SYMBOLS = ("BTC/USDT", "ETH/USDT")
FIXTURE_TIMEFRAMES = ("4h", "1d")
FIXTURE_ROWS = 900
START = datetime(2021, 1, 1, tzinfo=UTC)


def timeframe_delta(timeframe: str) -> timedelta:
    if timeframe == "4h":
        return timedelta(hours=4)
    if timeframe == "1d":
        return timedelta(days=1)
    raise ValueError(f"unsupported fixture timeframe: {timeframe}")


def make_rows(symbol: str, timeframe: str, rows: int = FIXTURE_ROWS) -> list[dict[str, object]]:
    interval = timeframe_delta(timeframe)
    symbol_offset = 800 if symbol.startswith("ETH") else 20000
    timeframe_scale = 1.25 if timeframe == "1d" else 1.0
    candles: list[dict[str, object]] = []
    for index in range(rows):
        timestamp = START + interval * index
        drift = index * 1.5 * timeframe_scale
        wave = math.sin(index / 11.0) * 45 * timeframe_scale
        close = symbol_offset + drift + wave
        open_price = close - math.cos(index / 7.0) * 12
        high = max(open_price, close) + 18 + (index % 5)
        low = min(open_price, close) - 18 - (index % 3)
        volume = 100 + (index % 17) * 3 + (5 if symbol.startswith("ETH") else 0)
        candles.append(
            {
                "timestamp": timestamp,
                "open": round(open_price, 8),
                "high": round(high, 8),
                "low": round(low, 8),
                "close": round(close, 8),
                "volume": round(float(volume), 8),
            }
        )
    return candles


def write_fixture(
    cache_dir: Path,
    exchange: str,
    symbol: str,
    timeframe: str,
    rows: int = FIXTURE_ROWS,
) -> Path:
    data = make_rows(symbol, timeframe, rows)
    path = cache_file_path(cache_dir, exchange, symbol, timeframe)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    pd.DataFrame(data).to_parquet(temp_path, index=False)
    os.replace(temp_path, path)

    metadata = {
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "first_timestamp": data[0]["timestamp"].isoformat(),
        "last_timestamp": data[-1]["timestamp"].isoformat(),
        "rows": rows,
        "fetched_at": "2026-05-30T00:00:00+00:00",
        "source": "fixture_generated",
    }
    metadata_path = metadata_file_path(cache_dir, exchange, symbol, timeframe)
    temp_metadata_path = metadata_path.with_suffix(f"{metadata_path.suffix}.tmp")
    temp_metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    os.replace(temp_metadata_path, metadata_path)
    return path


def generate_fixtures(cache_dir: Path = Path("data/raw/ohlcv")) -> list[Path]:
    written: list[Path] = []
    for symbol in FIXTURE_SYMBOLS:
        for timeframe in FIXTURE_TIMEFRAMES:
            written.append(write_fixture(cache_dir, FIXTURE_EXCHANGE, symbol, timeframe))
    return written


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic local OHLCV fixtures.")
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/ohlcv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in generate_fixtures(args.cache_dir):
        print(f"wrote fixture: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
