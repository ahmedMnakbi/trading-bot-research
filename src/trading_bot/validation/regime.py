from __future__ import annotations

import pandas as pd


def tag_regimes(
    candles: pd.DataFrame,
    *,
    trend_ma_period: int,
    volatility_window: int,
    high_volatility_quantile: float,
    low_volatility_quantile: float,
) -> pd.DataFrame:
    if "close" not in candles:
        raise ValueError("missing close column")
    tagged = candles.copy()
    close = tagged["close"]
    ma = close.rolling(window=trend_ma_period, min_periods=trend_ma_period).mean()
    slope = ma.diff()
    trend = pd.Series("unknown", index=tagged.index, dtype="object")
    trend[(close > ma) & (slope > 0)] = "uptrend"
    trend[(close < ma) & (slope < 0)] = "downtrend"
    trend[ma.notna() & (trend == "unknown")] = "range"

    returns = close.pct_change()
    volatility = returns.rolling(window=volatility_window, min_periods=volatility_window).std()
    high_threshold = volatility.quantile(high_volatility_quantile)
    low_threshold = volatility.quantile(low_volatility_quantile)
    volatility_regime = pd.Series("unknown", index=tagged.index, dtype="object")
    volatility_regime[volatility >= high_threshold] = "high_volatility"
    volatility_regime[volatility <= low_threshold] = "low_volatility"

    tagged["trend_regime"] = trend
    tagged["volatility_regime"] = volatility_regime
    return tagged


def regime_performance(
    *,
    trades: pd.DataFrame,
    equity_curve: pd.DataFrame,
    tagged_candles: pd.DataFrame,
) -> list[dict[str, object]]:
    if tagged_candles.empty:
        return []
    timestamp_to_regime = {
        row["timestamp"]: row["trend_regime"] for row in tagged_candles.to_dict(orient="records")
    }
    rows = []
    if trades.empty or "entry_timestamp" not in trades:
        return [
            _empty_regime_row(regime)
            for regime in sorted(set(tagged_candles["trend_regime"]) - {"unknown"})
        ]
    enriched = trades.copy()
    enriched["regime"] = enriched["entry_timestamp"].map(timestamp_to_regime).fillna("unknown")
    for regime, group in enriched.groupby("regime"):
        pnl = group["pnl"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        gross_loss = abs(float(losses.sum()))
        if gross_loss:
            profit_factor = float(wins.sum()) / gross_loss
        else:
            profit_factor = float("inf") if len(wins) else 0.0
        rows.append(
            {
                "regime": regime,
                "number_of_trades": int(len(group)),
                "total_return_pct": _total_return_pct(group),
                "win_rate_pct": float(len(wins) / len(group) * 100) if len(group) else 0.0,
                "profit_factor": profit_factor,
                "max_drawdown_pct": _regime_drawdown(equity_curve),
                "average_trade_return_pct": float((pnl / 1).mean()) if len(group) else 0.0,
            }
        )
    return rows


def _empty_regime_row(regime: str) -> dict[str, object]:
    return {
        "regime": regime,
        "number_of_trades": 0,
        "total_return_pct": 0.0,
        "win_rate_pct": 0.0,
        "profit_factor": 0.0,
        "max_drawdown_pct": 0.0,
        "average_trade_return_pct": 0.0,
    }


def _total_return_pct(trades: pd.DataFrame) -> float:
    return float(trades["pnl"].sum()) if not trades.empty else 0.0


def _regime_drawdown(equity_curve: pd.DataFrame) -> float:
    if equity_curve.empty:
        return 0.0
    running_max = equity_curve["equity"].cummax()
    drawdowns = (equity_curve["equity"] - running_max) / running_max * 100
    return abs(float(drawdowns.min()))
