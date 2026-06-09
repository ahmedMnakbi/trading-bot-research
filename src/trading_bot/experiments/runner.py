from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_bot.audit.integrity import write_artifact_manifest
from trading_bot.backtesting.engine import run_backtest_on_candles
from trading_bot.config.settings import Settings
from trading_bot.data.cache import OhlcvCache
from trading_bot.data.validation import validate_candles
from trading_bot.experiments.artifacts import write_campaign_artifacts
from trading_bot.experiments.campaign import build_experiment_matrix, matrix_as_dicts
from trading_bot.experiments.reporting import render_campaign_html, render_campaign_markdown
from trading_bot.experiments.selection import label_candidate
from trading_bot.strategies.registry import get_strategy
from trading_bot.validation.walk_forward import (
    aggregate_walk_forward_metrics,
    create_walk_forward_windows,
)


class CampaignError(RuntimeError):
    """Raised when a campaign cannot be started."""


def run_campaign(
    *,
    settings: Settings,
    config_snapshot: dict[str, Any],
    exchange: str,
    symbols: list[str] | None = None,
    timeframes: list[str] | None = None,
    strategies: list[str] | None = None,
) -> Path:
    if settings.mode.value == "live" or settings.live_trading_enabled:
        raise CampaignError("campaigns refuse live-trading configuration")
    selected_symbols = symbols or settings.experiments.symbols
    selected_timeframes = timeframes or settings.experiments.timeframes
    selected_strategies = strategies or settings.experiments.strategies
    matrix = build_experiment_matrix(
        exchange=exchange,
        symbols=selected_symbols,
        timeframes=selected_timeframes,
        strategies=selected_strategies,
        stages=settings.experiments.required_stages,
    )
    cache = OhlcvCache(settings.data.cache_dir)
    results: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    warnings: dict[str, list[str]] = {}
    labels: dict[str, dict[str, Any]] = {}
    benchmark_summary: dict[str, Any] = {}

    for experiment in matrix:
        experiment.status = "RUNNING"
        try:
            candles = cache.read(experiment.exchange, experiment.symbol, experiment.timeframe)
            if not candles:
                raise CampaignError("missing cached OHLCV")
            validate_candles(candles, experiment.timeframe, validate_continuity=True)
            metrics = _run_experiment(settings, candles, experiment)
            label, reasons = label_candidate(metrics, settings.experiments.review_gates)
            metrics["candidate_label"] = label
            metrics["candidate_label_reasons"] = reasons
            experiment.status = "COMPLETED"
            results.append({"experiment": experiment.__dict__, "metrics": metrics})
            warnings[experiment.experiment_id] = list(metrics.get("validation_warning_flags") or [])
            labels[experiment.experiment_id] = {"label": label, "reasons": reasons}
            benchmark_summary[experiment.experiment_id] = {
                "buy_and_hold_total_return_pct": metrics.get("buy_and_hold_total_return_pct"),
                "excess_return_vs_buy_and_hold_pct": metrics.get(
                    "excess_return_vs_buy_and_hold_pct"
                ),
            }
        except Exception as exc:
            experiment.status = "FAILED"
            failed.append({"experiment": experiment.__dict__, "error": str(exc)})
            labels[experiment.experiment_id] = {
                "label": "REJECTED",
                "reasons": ["experiment_failed"],
            }

    campaign_run_id = f"campaign_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = settings.experiments.output_dir / campaign_run_id
    metadata = {
        "campaign_run_id": campaign_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "exchange": exchange,
        "symbols": selected_symbols,
        "timeframes": selected_timeframes,
        "strategies": selected_strategies,
        "benchmarks": settings.experiments.benchmarks,
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "optimization_used": False,
        "paper_trading_used": False,
    }
    summary = {
        "campaign_run_id": campaign_run_id,
        "total_experiments": len(matrix),
        "completed": len(results),
        "failed": len(failed),
    }
    markdown = render_campaign_markdown(
        metadata=metadata,
        matrix=matrix_as_dicts(matrix),
        results=results,
        failed=failed,
        labels=labels,
        warnings=warnings,
    )
    html = render_campaign_html(labels=labels, warnings=warnings, failed=failed)
    output = write_campaign_artifacts(
        output_dir=output_dir,
        config_snapshot=config_snapshot,
        artifacts={
            "campaign_summary.json": summary,
            "experiment_matrix.json": matrix_as_dicts(matrix),
            "experiment_results.json": results,
            "benchmark_summary.json": benchmark_summary,
            "warning_summary.json": warnings,
            "candidate_labels.json": labels,
            "failed_runs.json": failed,
            "report.md": markdown,
            "report.html": html,
            "run_metadata.json": metadata,
        },
    )
    if settings.experiments.write_artifact_manifest:
        write_artifact_manifest(output)
    return output


def _run_experiment(settings: Settings, candles: list[Any], experiment: Any) -> dict[str, Any]:
    strategy = get_strategy(experiment.strategy, params=settings.strategy.params)
    backtest = run_backtest_on_candles(
        candles=candles,
        output_root=Path("data/processed/campaign-internal"),
        exchange=experiment.exchange,
        symbol=experiment.symbol,
        timeframe=experiment.timeframe,
        strategy=strategy,
        starting_equity=settings.backtesting.starting_equity,
        fee_bps=settings.execution.fee_bps,
        slippage_bps=settings.execution.slippage_bps,
        allow_shorting=False,
        allow_leverage=False,
        reject_orders_without_stop=settings.backtesting.reject_orders_without_stop,
        min_cash_pct=settings.backtesting.min_cash_pct,
        mark_to_market=settings.backtesting.mark_to_market,
        config_snapshot={},
        risk_per_trade_pct=settings.risk.risk_per_trade_pct,
        max_total_exposure_pct=settings.risk.max_total_exposure_pct,
        min_stop_distance_bps=settings.risk.min_stop_distance_bps,
        max_stop_distance_pct=settings.risk.max_stop_distance_pct,
        write_artifacts=False,
    )
    validation = _validation_metrics(settings, candles, experiment)
    benchmark = run_backtest_on_candles(
        candles=candles,
        output_root=Path("data/processed/campaign-internal"),
        exchange=experiment.exchange,
        symbol=experiment.symbol,
        timeframe=experiment.timeframe,
        strategy=get_strategy("buy_and_hold", params=settings.strategy.params),
        starting_equity=settings.backtesting.starting_equity,
        fee_bps=settings.execution.fee_bps,
        slippage_bps=settings.execution.slippage_bps,
        allow_shorting=False,
        allow_leverage=False,
        reject_orders_without_stop=settings.backtesting.reject_orders_without_stop,
        min_cash_pct=settings.backtesting.min_cash_pct,
        mark_to_market=settings.backtesting.mark_to_market,
        config_snapshot={},
        risk_per_trade_pct=settings.risk.risk_per_trade_pct,
        max_total_exposure_pct=settings.risk.max_total_exposure_pct,
        min_stop_distance_bps=settings.risk.min_stop_distance_bps,
        max_stop_distance_pct=settings.risk.max_stop_distance_pct,
        write_artifacts=False,
    )
    return {
        "backtest_total_return_pct": backtest.metrics.get("total_return_pct"),
        "backtest_max_drawdown_pct": backtest.metrics.get("max_drawdown_pct"),
        "backtest_profit_factor": backtest.metrics.get("profit_factor"),
        "backtest_trade_count": backtest.metrics.get("number_of_trades"),
        **validation,
        "buy_and_hold_total_return_pct": benchmark.metrics.get("total_return_pct"),
        "excess_return_vs_buy_and_hold_pct": (
            validation.get("validation_test_return_pct") - benchmark.metrics.get("total_return_pct")
            if validation.get("validation_test_return_pct") is not None
            else None
        ),
        "drawdown_difference_vs_buy_and_hold_pct": (
            validation.get("validation_test_max_drawdown_pct")
            - benchmark.metrics.get("max_drawdown_pct")
            if validation.get("validation_test_max_drawdown_pct") is not None
            else None
        ),
        "number_of_failed_stages": 0,
    }


def _validation_metrics(settings: Settings, candles: list[Any], experiment: Any) -> dict[str, Any]:
    windows = create_walk_forward_windows(
        len(candles),
        train_bars=settings.validation.walk_forward.train_bars,
        test_bars=settings.validation.walk_forward.test_bars,
        step_bars=settings.validation.walk_forward.step_bars,
    )
    window_results = []
    flags: list[str] = []
    for window in windows:
        test = run_backtest_on_candles(
            candles=candles[: window.test_end],
            output_root=Path("data/processed/campaign-internal"),
            exchange=experiment.exchange,
            symbol=experiment.symbol,
            timeframe=experiment.timeframe,
            strategy=get_strategy(experiment.strategy, params=settings.strategy.params),
            starting_equity=settings.backtesting.starting_equity,
            fee_bps=settings.execution.fee_bps,
            slippage_bps=settings.execution.slippage_bps,
            allow_shorting=False,
            allow_leverage=False,
            reject_orders_without_stop=settings.backtesting.reject_orders_without_stop,
            min_cash_pct=settings.backtesting.min_cash_pct,
            mark_to_market=settings.backtesting.mark_to_market,
            config_snapshot={},
            risk_per_trade_pct=settings.risk.risk_per_trade_pct,
            max_total_exposure_pct=settings.risk.max_total_exposure_pct,
            min_stop_distance_bps=settings.risk.min_stop_distance_bps,
            max_stop_distance_pct=settings.risk.max_stop_distance_pct,
            trade_start_index=window.test_start,
            write_artifacts=False,
        )
        if test.metrics.get("number_of_trades", 0) == 0:
            flags.append("ZERO_TRADES")
        window_results.append({"window": window.__dict__, "test_metrics": test.metrics})
    aggregate = aggregate_walk_forward_metrics(window_results)
    last = window_results[-1]["test_metrics"]
    return {
        "validation_number_of_windows": aggregate["number_of_windows"],
        "validation_test_return_pct": last.get("total_return_pct"),
        "validation_test_max_drawdown_pct": last.get("max_drawdown_pct"),
        "validation_median_test_return_pct": aggregate["median_test_return_pct"],
        "validation_worst_test_drawdown_pct": aggregate["worst_test_drawdown_pct"],
        "validation_consistency_score": aggregate["consistency_score"],
        "validation_total_test_trades": aggregate["total_test_trades"],
        "validation_profit_factor": last.get("profit_factor"),
        "validation_warning_flags": sorted(set(flags)),
    }
