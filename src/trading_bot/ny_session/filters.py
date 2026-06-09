from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import pandas as pd

from trading_bot.mt5.timezone import is_in_session, to_new_york_time
from trading_bot.ny_session.models import NySessionSignal, NySessionSignalResult


@dataclass(frozen=True)
class NySessionFilter:
    start: str
    end: str
    max_spread: int | None = None
    news_blackout: bool = False
    flat_at_session_close: bool = True

    def check(
        self,
        candles: pd.DataFrame,
        current_index: int,
        *,
        has_position: bool = False,
    ) -> NySessionSignalResult | None:
        current = candles.iloc[current_index]
        timestamp = _timestamp(current["timestamp"])
        if self.news_blackout:
            return NySessionSignalResult.skip_news()
        if self.max_spread is not None and "spread" in candles.columns:
            spread = current.get("spread")
            if pd.notna(spread) and int(spread) > self.max_spread:
                return NySessionSignalResult.skip_spread(int(spread), self.max_spread)
        in_session = is_in_session(timestamp, start=self.start, end=self.end)
        if not in_session:
            if has_position and self.flat_at_session_close:
                return NySessionSignalResult(
                    signal=NySessionSignal.SESSION_CLOSE,
                    reason="outside_configured_session",
                    metadata={"new_york_timestamp": to_new_york_time(timestamp).isoformat()},
                )
            return NySessionSignalResult.wait(
                "outside_configured_session",
                new_york_timestamp=to_new_york_time(timestamp).isoformat(),
            )
        return None


def _timestamp(value: object) -> datetime:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    raise ValueError(f"invalid timestamp value: {value}")
