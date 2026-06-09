from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trading_bot.backtesting.events import TradeIntent
from trading_bot.indicators.atr import average_true_range
from trading_bot.indicators.moving_average import exponential_moving_average
from trading_bot.portfolio.account import AccountState


@dataclass(frozen=True)
class EmaTrendStrategy:
    name: str = "ema_trend"
    ema_fast: int = 50
    ema_slow: int = 200
    atr_period: int = 14
    atr_stop_multiple: float = 2.5
    take_profit_r_multiple: float | None = None
    risk_fraction_override: float | None = None

    @classmethod
    def from_params(cls, params: dict[str, object]) -> EmaTrendStrategy:
        return cls(
            ema_fast=int(params.get("ema_fast", 50) or 50),
            ema_slow=int(params.get("ema_slow", 200) or 200),
            atr_period=int(params.get("atr_period", 14) or 14),
            atr_stop_multiple=float(params.get("atr_stop_multiple", 2.5) or 2.5),
            take_profit_r_multiple=_optional_float(params.get("take_profit_r_multiple")),
            risk_fraction_override=_optional_float(params.get("risk_fraction_override")),
        )

    def generate_signal(
        self, candles: pd.DataFrame, current_index: int, account: AccountState
    ) -> TradeIntent:
        min_rows = max(self.ema_slow, self.atr_period, 2)
        if len(candles) < min_rows:
            return TradeIntent.hold("insufficient_history")
        close = candles["close"]
        fast = exponential_moving_average(close, self.ema_fast)
        slow = exponential_moving_average(close, self.ema_slow)
        atr = average_true_range(candles, self.atr_period)
        if fast.iloc[-self.ema_slow :].isna().any() or slow.iloc[-1:].isna().any():
            return TradeIntent.hold("indicator_unavailable")
        current_close = float(close.iloc[-1])
        previous_close = float(close.iloc[-2])
        current_fast = float(fast.iloc[-1])
        current_slow = float(slow.iloc[-1])
        previous_fast = float(fast.iloc[-2])
        previous_slow = float(slow.iloc[-2])
        current_atr = atr.iloc[-1]
        if pd.isna(current_atr) or current_atr <= 0:
            return TradeIntent.hold("indicator_unavailable")
        if account.position is not None:
            if current_fast < current_slow or current_close < current_fast:
                return TradeIntent(action="EXIT", reason="strategy_exit")
            return TradeIntent.hold("in_position")
        crossed_or_regime_changed = (
            previous_close <= previous_fast or previous_fast <= previous_slow
        )
        if (
            current_fast > current_slow
            and current_close > current_fast
            and crossed_or_regime_changed
        ):
            stop_loss = current_close - self.atr_stop_multiple * float(current_atr)
            if stop_loss <= 0 or stop_loss >= current_close:
                return TradeIntent.hold("invalid_stop")
            risk_per_unit = current_close - stop_loss
            take_profit = None
            if self.take_profit_r_multiple is not None:
                take_profit = current_close + self.take_profit_r_multiple * risk_per_unit
            return TradeIntent(
                action="BUY",
                reason="strategy_entry",
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_fraction_pct=self.risk_fraction_override,
                metadata={"ema_fast": current_fast, "ema_slow": current_slow},
            )
        return TradeIntent.hold("no_trend_signal")


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)
