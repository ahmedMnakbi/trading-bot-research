from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from trading_bot.data.cache import OhlcvCache
from trading_bot.data.validation import build_quality_report


def inspect_cached_data(
    *,
    cache_dir: str | Path,
    exchange: str,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    cache = OhlcvCache(cache_dir)
    candles = cache.read(exchange, symbol, timeframe)
    report = build_quality_report(candles, timeframe)
    payload = asdict(report)
    payload["cache_file_path"] = str(cache.path_for(exchange, symbol, timeframe))
    return payload
