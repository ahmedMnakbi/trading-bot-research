from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from trading_bot.backtesting.engine import run_backtest_on_candles
from trading_bot.backtesting.results import new_run_id
from trading_bot.config.settings import Settings
from trading_bot.data.cache import OhlcvCache, candles_to_dataframe
from trading_bot.data.validation import validate_candles
from trading_bot.strategies.registry import get_strategy
from trading_bot.validation.comparison import compare_to_benchmark, warning_flags
from trading_bot.validation.regime import regime_performance, tag_regimes
from trading_bot.validation.splits import chronological_train_test_split
from trading_bot.validation.walk_forward import (
    aggregate_walk_forward_metrics,
    create_walk_forward_windows,
)


class ValidationError(RuntimeError):
    """Raised when local validation cannot run."""


def run_validation_from_cache(
    *,
    settings: Settings,
    config_snapshot: dict[str, Any],
    exchange: str,
    symbol: str,
    timeframe: str,
    output_root: str | Path = Path("data/processed/validations"),
    run_id: str | None = None,
) -> Path:
    _validate_strategy_names(settings.validation.strategies + settings.validation.benchmarks)
    cache = OhlcvCache(settings.data.cache_dir)
    path = cache.path_for(exchange, symbol, timeframe)
    if not path.exists():
        raise ValidationError(f"missing cache file: {path}")
    candles = cache.read(exchange, symbol, timeframe)
    if not candles:
        raise ValidationError("empty OHLCV dataset")
    validate_candles(candles, timeframe, validate_continuity=True)
    selected_run_id = run_id or new_run_id()
    output_dir = Path(output_root) / selected_run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    split = chronological_train_test_split(
        len(candles),
        train_pct=settings.validation.train_pct,
        test_pct=settings.validation.test_pct,
        min_train_bars=settings.validation.min_train_bars,
        min_test_bars=settings.validation.min_test_bars,
    )
    benchmark_test_results = {
        benchmark: _run_window(
            settings=settings,
            candles=candles[: split.test_end],
            trade_start_index=split.test_start,
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=benchmark,
            config_snapshot=config_snapshot,
        )
        for benchmark in settings.validation.benchmarks
    }
    static_results: dict[str, Any] = {}
    comparisons: dict[str, Any] = {}
    warnings: dict[str, list[str]] = {}
    regime_results: dict[str, Any] = {}
    tagged = tag_regimes(
        candles_to_dataframe(candles),
        trend_ma_period=settings.validation.regime.trend_ma_period,
        volatility_window=settings.validation.regime.volatility_window,
        high_volatility_quantile=settings.validation.regime.high_volatility_quantile,
        low_volatility_quantile=settings.validation.regime.low_volatility_quantile,
    )

    for strategy_name in settings.validation.strategies:
        train = _run_window(
            settings=settings,
            candles=candles[split.train_start : split.train_end],
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            config_snapshot=config_snapshot,
        )
        test = _run_window(
            settings=settings,
            candles=candles[: split.test_end],
            trade_start_index=split.test_start,
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            config_snapshot=config_snapshot,
        )
        static_results[strategy_name] = {
            "train_metrics": train.metrics,
            "test_metrics": test.metrics,
            "degradation": _degradation(train.metrics, test.metrics),
        }
        buy_and_hold = benchmark_test_results.get("buy_and_hold")
        if buy_and_hold is not None:
            comparisons[strategy_name] = compare_to_benchmark(
                strategy_metrics=test.metrics,
                benchmark_metrics=buy_and_hold.metrics,
            )
        warnings[strategy_name] = warning_flags(
            train_metrics=train.metrics,
            test_metrics=test.metrics,
            buy_and_hold_metrics=buy_and_hold.metrics if buy_and_hold else None,
        )
        regime_results[strategy_name] = regime_performance(
            trades=test.trades,
            equity_curve=test.equity_curve,
            tagged_candles=tagged.iloc[split.test_start : split.test_end],
        )

    walk_forward_results: dict[str, Any] = {}
    if settings.validation.walk_forward.enabled:
        windows = create_walk_forward_windows(
            len(candles),
            train_bars=settings.validation.walk_forward.train_bars,
            test_bars=settings.validation.walk_forward.test_bars,
            step_bars=settings.validation.walk_forward.step_bars,
        )
        for strategy_name in settings.validation.strategies:
            window_results = []
            for window in windows:
                train = _run_window(
                    settings=settings,
                    candles=candles[window.train_start : window.train_end],
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    config_snapshot=config_snapshot,
                )
                test = _run_window(
                    settings=settings,
                    candles=candles[: window.test_end],
                    trade_start_index=window.test_start,
                    exchange=exchange,
                    symbol=symbol,
                    timeframe=timeframe,
                    strategy_name=strategy_name,
                    config_snapshot=config_snapshot,
                )
                window_results.append(
                    {
                        "window": window.__dict__,
                        "train_metrics": train.metrics,
                        "test_metrics": test.metrics,
                    }
                )
            walk_forward_results[strategy_name] = {
                "windows": window_results,
                "aggregate": aggregate_walk_forward_metrics(window_results),
            }

    metadata = {
        "run_id": selected_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "exchange": exchange,
        "symbol": symbol,
        "timeframe": timeframe,
        "strategies": settings.validation.strategies,
        "benchmarks": settings.validation.benchmarks,
        "data_first_timestamp": candles[0].timestamp.isoformat(),
        "data_last_timestamp": candles[-1].timestamp.isoformat(),
        "data_rows": len(candles),
        "live_trading": False,
        "optimization_used": False,
    }
    summary = {
        "run_id": selected_run_id,
        "strategies": list(static_results),
        "benchmarks": settings.validation.benchmarks,
        "warnings_count": sum(len(value) for value in warnings.values()),
    }
    _write_json(output_dir / "validation_summary.json", summary)
    _write_json(output_dir / "static_split_results.json", static_results)
    _write_json(output_dir / "walk_forward_results.json", walk_forward_results)
    _write_json(output_dir / "benchmark_comparison.json", comparisons)
    _write_json(output_dir / "regime_performance.json", regime_results)
    _write_json(output_dir / "warnings.json", warnings)
    _write_json(output_dir / "run_metadata.json", metadata)
    (output_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config_snapshot, sort_keys=False), encoding="utf-8"
    )
    return output_dir


def _run_window(
    *,
    settings: Settings,
    candles: list[Any],
    trade_start_index: int = 0,
    exchange: str,
    symbol: str,
    timeframe: str,
    strategy_name: str,
    config_snapshot: dict[str, Any],
):
    if len(candles) < 2:
        raise ValidationError("insufficient bars for validation window")
    return run_backtest_on_candles(
        candles=candles,
        output_root=Path("data/processed/validation-internal"),
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        strategy=get_strategy(strategy_name, params=settings.strategy.params),
        starting_equity=settings.backtesting.starting_equity,
        fee_bps=settings.execution.fee_bps,
        slippage_bps=settings.execution.slippage_bps,
        allow_shorting=settings.backtesting.allow_shorting,
        allow_leverage=settings.backtesting.allow_leverage,
        reject_orders_without_stop=settings.backtesting.reject_orders_without_stop,
        min_cash_pct=settings.backtesting.min_cash_pct,
        mark_to_market=settings.backtesting.mark_to_market,
        config_snapshot=config_snapshot,
        risk_per_trade_pct=settings.risk.risk_per_trade_pct,
        max_total_exposure_pct=settings.risk.max_total_exposure_pct,
        min_stop_distance_bps=settings.risk.min_stop_distance_bps,
        max_stop_distance_pct=settings.risk.max_stop_distance_pct,
        trade_start_index=trade_start_index,
        write_artifacts=False,
    )


def _degradation(train_metrics: dict[str, Any], test_metrics: dict[str, Any]) -> dict[str, Any]:
    train_return = float(train_metrics["total_return_pct"])
    test_return = float(test_metrics["total_return_pct"])
    train_pf = float(train_metrics["profit_factor"])
    test_pf = float(test_metrics["profit_factor"])
    return {
        "train_total_return_pct": train_return,
        "test_total_return_pct": test_return,
        "train_max_drawdown_pct": train_metrics["max_drawdown_pct"],
        "test_max_drawdown_pct": test_metrics["max_drawdown_pct"],
        "train_profit_factor": train_pf,
        "test_profit_factor": test_pf,
        "return_degradation_pct": train_return - test_return,
        "drawdown_worsening_pct": (
            float(test_metrics["max_drawdown_pct"]) - float(train_metrics["max_drawdown_pct"])
        ),
        "profit_factor_degradation_pct": train_pf - test_pf,
    }


def _validate_strategy_names(names: list[str]) -> None:
    for name in names:
        get_strategy(name)


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and value == float("inf"):
        return "Infinity"
    if isinstance(value, Path):
        return os.fspath(value)
    return value
