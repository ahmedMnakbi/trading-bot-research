from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from trading_bot.backtesting.results import _json_safe
from trading_bot.mt5.backtesting import (
    Mt5BacktestError,
    Mt5BacktestMarketModel,
    run_mt5_backtest_on_bars,
)
from trading_bot.mt5.cache import Mt5RatesCache
from trading_bot.mt5.data import Mt5RateBar, validate_mt5_bars
from trading_bot.ny_session.strategies import get_ny_session_strategy
from trading_bot.validation.splits import chronological_train_test_split
from trading_bot.validation.walk_forward import (
    aggregate_walk_forward_metrics,
    create_walk_forward_windows,
)


class Mt5ValidationError(RuntimeError):
    """Raised when MT5 validation or campaign review cannot run."""


def run_mt5_validation_from_cache(
    *,
    cache_dir: str | Path,
    output_root: str | Path,
    broker: str,
    symbol: str,
    timeframe: str,
    strategies: list[str],
    market_model: Mt5BacktestMarketModel | None = None,
    train_pct: int = 70,
    test_pct: int = 30,
    min_train_bars: int = 40,
    min_test_bars: int = 20,
    walk_forward_train_bars: int = 40,
    walk_forward_test_bars: int = 20,
    walk_forward_step_bars: int = 20,
    config_snapshot: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> Path:
    bars = _load_bars(cache_dir, broker, symbol, timeframe)
    selected_run_id = run_id or f"mt5_validation_{_stamp()}"
    output_dir = Path(output_root) / selected_run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    model = market_model or Mt5BacktestMarketModel()
    split = chronological_train_test_split(
        len(bars),
        train_pct=train_pct,
        test_pct=test_pct,
        min_train_bars=min_train_bars,
        min_test_bars=min_test_bars,
    )
    windows = create_walk_forward_windows(
        len(bars),
        train_bars=walk_forward_train_bars,
        test_bars=walk_forward_test_bars,
        step_bars=walk_forward_step_bars,
    )
    static_results: dict[str, Any] = {}
    walk_forward_results: dict[str, Any] = {}
    warnings: dict[str, list[str]] = {}

    for strategy_name in strategies:
        strategy = get_ny_session_strategy(strategy_name)
        train = _run_window(
            bars[split.train_start : split.train_end],
            broker,
            symbol,
            timeframe,
            strategy,
            model,
        )
        test = _run_window(
            bars[: split.test_end],
            broker,
            symbol,
            timeframe,
            strategy,
            model,
            trade_start_index=split.test_start,
        )
        static_results[strategy_name] = {
            "train_metrics": train.metrics,
            "test_metrics": test.metrics,
        }
        window_results = []
        for window in windows:
            window_test = _run_window(
                bars[: window.test_end],
                broker,
                symbol,
                timeframe,
                strategy,
                model,
                trade_start_index=window.test_start,
            )
            window_results.append(
                {
                    "window": window.__dict__,
                    "test_metrics": window_test.metrics,
                }
            )
        aggregate = aggregate_walk_forward_metrics(window_results)
        walk_forward_results[strategy_name] = {
            "windows": window_results,
            "aggregate": aggregate,
        }
        warnings[strategy_name] = _warnings(aggregate)

    metadata = _metadata(selected_run_id, broker, symbol, timeframe, bars, strategies)
    _write_json(
        output_dir / "validation_summary.json",
        {
            "run_id": selected_run_id,
            "strategies": strategies,
            "walk_forward_windows": len(windows),
            "warnings_count": sum(len(value) for value in warnings.values()),
        },
    )
    _write_json(output_dir / "static_split_results.json", static_results)
    _write_json(output_dir / "walk_forward_results.json", walk_forward_results)
    _write_json(output_dir / "warnings.json", warnings)
    _write_json(output_dir / "run_metadata.json", metadata)
    (output_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config_snapshot or {}, sort_keys=False),
        encoding="utf-8",
    )
    return output_dir


def run_mt5_campaign_from_cache(
    *,
    cache_dir: str | Path,
    output_root: str | Path,
    broker: str,
    symbols: list[str],
    timeframes: list[str],
    strategies: list[str],
    market_model: Mt5BacktestMarketModel | None = None,
    min_validation_windows: int = 1,
    min_total_test_trades: int = 1,
    config_snapshot: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> Path:
    selected_run_id = run_id or f"mt5_campaign_{_stamp()}"
    output_dir = Path(output_root) / selected_run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    results: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    labels: dict[str, dict[str, Any]] = {}
    warnings: dict[str, list[str]] = {}
    model = market_model or Mt5BacktestMarketModel()

    for symbol in symbols:
        for timeframe in timeframes:
            for strategy_name in strategies:
                experiment_id = f"{broker}:{symbol}:{timeframe}:{strategy_name}"
                try:
                    bars = _load_bars(cache_dir, broker, symbol, timeframe)
                    strategy = get_ny_session_strategy(strategy_name)
                    windows = create_walk_forward_windows(
                        len(bars),
                        train_bars=40,
                        test_bars=20,
                        step_bars=20,
                    )
                    window_results = [
                        {
                            "window": window.__dict__,
                            "test_metrics": _run_window(
                                bars[: window.test_end],
                                broker,
                                symbol,
                                timeframe,
                                strategy,
                                model,
                                trade_start_index=window.test_start,
                            ).metrics,
                        }
                        for window in windows
                    ]
                    aggregate = aggregate_walk_forward_metrics(window_results)
                    flags = _warnings(aggregate)
                    label, reasons = _label(
                        aggregate,
                        flags,
                        min_validation_windows,
                        min_total_test_trades,
                    )
                    payload = {
                        "experiment_id": experiment_id,
                        "broker": broker,
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "strategy": strategy_name,
                        "aggregate": aggregate,
                        "candidate_label": label,
                        "candidate_label_reasons": reasons,
                    }
                    results.append(payload)
                    labels[experiment_id] = {"label": label, "reasons": reasons}
                    warnings[experiment_id] = flags
                except Exception as exc:
                    failed.append({"experiment_id": experiment_id, "error": str(exc)})
                    labels[experiment_id] = {"label": "REJECTED", "reasons": ["experiment_failed"]}
    metadata = {
        "campaign_run_id": selected_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "broker": broker,
        "symbols": symbols,
        "timeframes": timeframes,
        "strategies": strategies,
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "optimization_used": False,
    }
    _write_json(
        output_dir / "campaign_summary.json",
        {
            "campaign_run_id": selected_run_id,
            "completed": len(results),
            "failed": len(failed),
        },
    )
    _write_json(output_dir / "experiment_results.json", results)
    _write_json(output_dir / "candidate_labels.json", labels)
    _write_json(output_dir / "warning_summary.json", warnings)
    _write_json(output_dir / "failed_runs.json", failed)
    _write_json(output_dir / "run_metadata.json", metadata)
    (output_dir / "config_snapshot.yaml").write_text(
        yaml.safe_dump(config_snapshot or {}, sort_keys=False),
        encoding="utf-8",
    )
    return output_dir


def _load_bars(cache_dir: str | Path, broker: str, symbol: str, timeframe: str) -> list[Mt5RateBar]:
    cache = Mt5RatesCache(cache_dir)
    path = cache.path_for(broker, symbol, timeframe)
    if not path.exists():
        raise Mt5ValidationError(f"missing MT5 cache file: {path}")
    bars = cache.read(broker, symbol, timeframe)
    validate_mt5_bars(bars, timeframe, validate_continuity=True)
    return bars


def _run_window(
    bars: list[Mt5RateBar],
    broker: str,
    symbol: str,
    timeframe: str,
    strategy: Any,
    market_model: Mt5BacktestMarketModel,
    *,
    trade_start_index: int = 0,
):
    if trade_start_index:
        bars = bars[:]
    if len(bars) < 2:
        raise Mt5BacktestError("insufficient MT5 bars for validation")
    result = run_mt5_backtest_on_bars(
        bars=bars,
        output_root=Path("data/processed/mt5-validation-internal"),
        broker=broker,
        symbol=symbol,
        timeframe=timeframe,
        strategy=strategy,
        market_model=market_model,
        config_snapshot={},
        trade_start_index=trade_start_index,
        write_artifacts=False,
    )
    return result


def _warnings(aggregate: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if aggregate["total_test_trades"] == 0:
        flags.append("ZERO_TRADES")
    if aggregate["consistency_score"] <= 0:
        flags.append("NO_POSITIVE_WINDOWS")
    return flags


def _label(
    aggregate: dict[str, Any],
    flags: list[str],
    min_validation_windows: int,
    min_total_test_trades: int,
) -> tuple[str, list[str]]:
    if "ZERO_TRADES" in flags:
        return "REJECTED", ["zero_validation_trades"]
    reasons: list[str] = []
    if aggregate["number_of_windows"] < min_validation_windows:
        reasons.append("too_few_validation_windows")
    if aggregate["total_test_trades"] < min_total_test_trades:
        reasons.append("too_few_test_trades")
    if reasons:
        return "NEEDS_MORE_DATA", reasons
    return "PAPER_OBSERVATION_ONLY", ["passed_research_review_gates"]


def _metadata(
    run_id: str,
    broker: str,
    symbol: str,
    timeframe: str,
    bars: list[Mt5RateBar],
    strategies: list[str],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "broker": broker,
        "symbol": symbol,
        "timeframe": timeframe,
        "strategies": strategies,
        "data_rows": len(bars),
        "data_first_timestamp": bars[0].timestamp.isoformat(),
        "data_last_timestamp": bars[-1].timestamp.isoformat(),
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "optimization_used": False,
    }


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex[:8]
