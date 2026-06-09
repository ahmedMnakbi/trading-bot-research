from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console

from trading_bot.audit.integrity import verify_artifact_manifest, write_artifact_manifest
from trading_bot.audit.reporting import run_safety_audit
from trading_bot.backtesting.engine import BacktestError, run_backtest_from_cache
from trading_bot.config.profiles import dump_effective_config, effective_config, list_profiles
from trading_bot.config.settings import load_settings, load_yaml
from trading_bot.data.cache import OhlcvCache
from trading_bot.data.ccxt_provider import CcxtOhlcvProvider, MarketDataError
from trading_bot.data.models import OhlcvCandle
from trading_bot.data.provider import MarketDataProvider
from trading_bot.data.reporting import inspect_cached_data
from trading_bot.data.validation import (
    drop_partial_latest_candle,
    timeframe_to_timedelta,
    validate_candles,
)
from trading_bot.execution.simulated import SimulatedExecutionClient
from trading_bot.experiments.runner import CampaignError, run_campaign
from trading_bot.incident.reporting import write_incident_replay
from trading_bot.mt5.backtesting import (
    Mt5BacktestError,
    Mt5BacktestMarketModel,
    run_mt5_backtest_from_cache,
)
from trading_bot.mt5.cache import Mt5RatesCache
from trading_bot.mt5.connection import Mt5ReadOnlyConnector, Mt5ReadOnlyError
from trading_bot.mt5.data import Mt5RatesError, Mt5RatesProvider
from trading_bot.mt5.demo_monitor import (
    Mt5DemoMonitorStore,
    new_mt5_demo_monitor_state,
    run_mt5_demo_monitor_once,
)
from trading_bot.mt5.models import load_mt5_readonly_config
from trading_bot.mt5.validation import (
    Mt5ValidationError,
    run_mt5_campaign_from_cache,
    run_mt5_validation_from_cache,
)
from trading_bot.ops.archive import archive_run
from trading_bot.ops.run_registry import (
    find_run,
    latest_report,
    load_or_build_registry,
    write_registry,
)
from trading_bot.ops.safe_commands import safe_workflow
from trading_bot.ops.summary import format_run
from trading_bot.paper.decision_log import PaperDecisionLogger
from trading_bot.paper.engine import PaperTradingEngine, PaperTradingError
from trading_bot.paper.portfolio_engine import (
    PortfolioPaperTradingEngine,
    PortfolioPaperTradingError,
)
from trading_bot.paper.store import PaperStateStore, PortfolioPaperStateStore
from trading_bot.release.final_check import run_final_nonlive_check, run_install_check
from trading_bot.release.human_review import export_human_review_package
from trading_bot.release.mt5_final_audit import (
    Mt5FinalAuditPackageError,
    export_mt5_final_audit_package,
)
from trading_bot.release.package import ReleasePackageError, build_release_candidate
from trading_bot.release.smoke import ReleaseSmokeError, run_nonlive_smoke
from trading_bot.release.verify import ReleaseVerificationError, verify_release_candidate
from trading_bot.reporting.paper_report import PaperReportError, generate_paper_report
from trading_bot.reporting.portfolio_paper_report import (
    PortfolioPaperReportError,
    generate_portfolio_paper_report,
)
from trading_bot.strategies.base import get_strategy
from trading_bot.testing.chaos_runner import FailureScenarioError, run_failure_scenarios
from trading_bot.utils.logging import configure_logging, get_logger
from trading_bot.validation.reporting import ValidationError as LocalValidationError
from trading_bot.validation.reporting import run_validation_from_cache
from trading_bot.version import __version__

app = typer.Typer(help="Safety-first experimental trading bot CLI.")
console = Console()


@app.callback()
def main() -> None:
    """Trading bot command group."""


@app.command("validate-config")
def validate_config(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    profile: Annotated[str | None, typer.Option(help="Config profile overlay name.")] = None,
) -> None:
    """Validate configuration and safety gates."""
    try:
        settings = load_settings(config, profile=profile)
    except (ValidationError, ValueError) as exc:
        console.print("[red]Configuration validation failed.[/red]")
        raise typer.Exit(code=1) from exc

    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="config", mode=settings.mode.value)
    logger.info("configuration_validated", config_path=str(config))
    console.print(f"[green]Configuration valid.[/green] mode={settings.mode.value}")


@app.command("version")
def version_command() -> None:
    """Print version and non-live safety metadata."""
    console.print(f"trading-bot {__version__}")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")


@app.command("mt5-readonly-check")
def mt5_readonly_check_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to MT5 read-only YAML configuration file.",
        ),
    ] = Path("config/mt5_readonly.yaml"),
) -> None:
    """Validate MT5 read-only setup and discover public terminal symbols."""
    try:
        mt5_config = load_mt5_readonly_config(config)
    except (ValidationError, ValueError) as exc:
        console.print("[red]MT5 read-only configuration validation failed.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc

    console.print("[green]MT5 read-only configuration valid.[/green]")
    console.print("live_trading: false")
    console.print("execution_enabled: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")
    console.print("order_functions_enabled: false")

    connector = Mt5ReadOnlyConnector(mt5_config)
    if not mt5_config.terminal.initialize:
        console.print("mt5_package_available: not_checked")
        console.print("terminal_connection_available: skipped")
        console.print("symbols_discovered: 0")
        return

    try:
        status = connector.initialize()
        symbols = connector.discover_symbols() if mt5_config.discovery.enabled else []
    except Mt5ReadOnlyError as exc:
        console.print(f"[red]MT5 read-only check failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        connector.shutdown()

    console.print(f"mt5_package_available: {str(status.package_available).lower()}")
    console.print(f"terminal_connection_available: {str(status.terminal_available).lower()}")
    console.print(f"terminal_connected: {str(status.connected).lower()}")
    if status.terminal_name:
        console.print(f"terminal_name: {status.terminal_name}")
    if status.company:
        console.print(f"terminal_company: {status.company}")
    if status.server:
        console.print(f"terminal_server: {status.server}")
    console.print(f"symbols_discovered: {len(symbols)}")
    for symbol in symbols[:20]:
        description = symbol.description or ""
        console.print(f"{symbol.name}\t{symbol.asset_class.value}\t{description}")


@app.command("fetch-mt5-rates")
def fetch_mt5_rates_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to MT5 read-only YAML configuration file.",
        ),
    ] = Path("config/mt5_readonly.yaml"),
    broker: Annotated[str, typer.Option(help="Local cache namespace for the MT5 broker.")] = "mt5",
    symbol: Annotated[str, typer.Option(help="Broker-specific MT5 symbol.")] = "EURUSD",
    timeframe: Annotated[str, typer.Option(help="MT5 timeframe, for example 5m or 1h.")] = "5m",
    since_days: Annotated[int, typer.Option(help="Number of days of history to request.")] = 30,
    cache_dir: Annotated[
        Path, typer.Option(help="Local MT5 rates cache directory.")
    ] = Path("data/raw/mt5_rates"),
) -> None:
    """Fetch read-only MT5 historical rates into the local cache."""
    try:
        mt5_config = load_mt5_readonly_config(config)
        connector = Mt5ReadOnlyConnector(mt5_config)
        status = connector.initialize()
        end = datetime.now(UTC)
        start = end - timedelta(days=since_days)
        provider = Mt5RatesProvider()
        bars = provider.fetch_rates(symbol=symbol, timeframe=timeframe, start=start, end=end)
        merged = Mt5RatesCache(cache_dir).merge_and_write(
            broker,
            symbol,
            timeframe,
            bars,
            validate_continuity=False,
        )
    except (ValidationError, ValueError, Mt5ReadOnlyError, Mt5RatesError) as exc:
        console.print(f"[red]MT5 rates fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if "connector" in locals():
            connector.shutdown()

    cache = Mt5RatesCache(cache_dir)
    console.print("[green]MT5 rates cached.[/green]")
    console.print(f"terminal_available: {str(status.terminal_available).lower()}")
    console.print(f"rows: {len(merged)}")
    console.print(f"cache file path: {cache.path_for(broker, symbol, timeframe)}")
    console.print(f"metadata file path: {cache.metadata_path_for(broker, symbol, timeframe)}")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")


@app.command("inspect-mt5-data")
def inspect_mt5_data_command(
    broker: Annotated[str, typer.Option(help="Local cache namespace for the MT5 broker.")] = "mt5",
    symbol: Annotated[str, typer.Option(help="Broker-specific MT5 symbol.")] = "EURUSD",
    timeframe: Annotated[str, typer.Option(help="MT5 timeframe, for example 5m or 1h.")] = "5m",
    cache_dir: Annotated[
        Path, typer.Option(help="Local MT5 rates cache directory.")
    ] = Path("data/raw/mt5_rates"),
) -> None:
    """Inspect cached MT5 historical rates."""
    try:
        report = Mt5RatesCache(cache_dir).inspect(broker, symbol, timeframe)
    except ValueError as exc:
        console.print(f"[red]MT5 data inspection failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    for key, value in report.items():
        console.print(f"{key}: {value}")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")


@app.command("run-mt5-backtest")
def run_mt5_backtest_command(
    broker: Annotated[str, typer.Option(help="Local cache namespace for the MT5 broker.")] = "mt5",
    symbol: Annotated[str, typer.Option(help="Broker-specific MT5 symbol.")] = "EURUSD",
    timeframe: Annotated[str, typer.Option(help="MT5 timeframe used in cache path.")] = "5m",
    strategy: Annotated[
        str, typer.Option(help="NY-session strategy name.")
    ] = "opening_range_breakout",
    cache_dir: Annotated[
        Path, typer.Option(help="Local MT5 rates cache directory.")
    ] = Path("data/raw/mt5_rates"),
    output_root: Annotated[
        Path, typer.Option(help="Output directory for MT5 backtest artifacts.")
    ] = Path("data/processed/mt5_backtests"),
    starting_equity: Annotated[float, typer.Option(help="Simulated starting equity.")] = 10_000,
    risk_per_trade_pct: Annotated[float, typer.Option(help="Simulated risk per trade pct.")] = 0.25,
    fee_bps: Annotated[float, typer.Option(help="Simulated fee basis points.")] = 0,
    slippage_points: Annotated[float, typer.Option(help="Simulated slippage in price points.")] = 0,
    point_value: Annotated[float, typer.Option(help="PnL value per price point per lot.")] = 1,
    min_lot: Annotated[float, typer.Option(help="Minimum simulated lot size.")] = 0.01,
    lot_step: Annotated[float, typer.Option(help="Simulated lot increment.")] = 0.01,
    min_stop_distance_points: Annotated[
        float, typer.Option(help="Minimum simulated stop distance in price points.")
    ] = 0,
    allow_shorting: Annotated[
        bool, typer.Option(help="Allow short signals in research simulation only.")
    ] = False,
) -> None:
    """Run a local MT5 cached-data research backtest with no broker execution."""
    try:
        result = run_mt5_backtest_from_cache(
            cache_dir=cache_dir,
            output_root=output_root,
            broker=broker,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy,
            market_model=Mt5BacktestMarketModel(
                starting_equity=starting_equity,
                risk_per_trade_pct=risk_per_trade_pct,
                fee_bps=fee_bps,
                slippage_points=slippage_points,
                point_value=point_value,
                min_lot=min_lot,
                lot_step=lot_step,
                min_stop_distance_points=min_stop_distance_points,
                allow_shorting=allow_shorting,
            ),
            config_snapshot={
                "broker": broker,
                "symbol": symbol,
                "timeframe": timeframe,
                "strategy": strategy,
                "live_trading": False,
                "real_orders_enabled": False,
                "uses_private_api": False,
            },
        )
    except (Mt5BacktestError, ValueError) as exc:
        console.print(f"[red]MT5 backtest failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print("[green]MT5 backtest complete.[/green]")
    console.print(f"run_id: {result.run_id}")
    console.print(f"total_return_pct: {result.metrics['total_return_pct']}")
    console.print(f"max_drawdown_pct: {result.metrics['max_drawdown_pct']}")
    console.print(f"number_of_trades: {result.metrics['number_of_trades']}")
    console.print(f"artifact path: {result.output_dir}")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")


@app.command("run-mt5-validation")
def run_mt5_validation_command(
    broker: Annotated[str, typer.Option(help="Local cache namespace for the MT5 broker.")] = "mt5",
    symbol: Annotated[str, typer.Option(help="Broker-specific MT5 symbol.")] = "EURUSD",
    timeframe: Annotated[str, typer.Option(help="MT5 timeframe used in cache path.")] = "5m",
    strategies: Annotated[
        str, typer.Option(help="Comma-separated NY-session strategies.")
    ] = "opening_range_breakout,vwap_trend_continuation",
    cache_dir: Annotated[
        Path, typer.Option(help="Local MT5 rates cache directory.")
    ] = Path("data/raw/mt5_rates"),
    output_root: Annotated[
        Path, typer.Option(help="Output directory for MT5 validation artifacts.")
    ] = Path("data/processed/mt5_validations"),
) -> None:
    """Run local MT5 cached-data validation and walk-forward review."""
    selected_strategies = [item.strip() for item in strategies.split(",") if item.strip()]
    try:
        output_dir = run_mt5_validation_from_cache(
            cache_dir=cache_dir,
            output_root=output_root,
            broker=broker,
            symbol=symbol,
            timeframe=timeframe,
            strategies=selected_strategies,
            config_snapshot={
                "broker": broker,
                "symbol": symbol,
                "timeframe": timeframe,
                "strategies": selected_strategies,
                "live_trading": False,
                "real_orders_enabled": False,
                "uses_private_api": False,
            },
        )
    except (Mt5ValidationError, Mt5BacktestError, ValueError) as exc:
        console.print(f"[red]MT5 validation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]MT5 validation complete.[/green]")
    console.print(f"artifact path: {output_dir}")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")


@app.command("run-mt5-campaign")
def run_mt5_campaign_command(
    broker: Annotated[str, typer.Option(help="Local cache namespace for the MT5 broker.")] = "mt5",
    symbols: Annotated[
        str,
        typer.Option(help="Comma-separated broker-specific symbols."),
    ] = "EURUSD",
    timeframes: Annotated[str, typer.Option(help="Comma-separated MT5 timeframes.")] = "5m",
    strategies: Annotated[
        str, typer.Option(help="Comma-separated NY-session strategies.")
    ] = "opening_range_breakout,vwap_trend_continuation",
    cache_dir: Annotated[
        Path, typer.Option(help="Local MT5 rates cache directory.")
    ] = Path("data/raw/mt5_rates"),
    output_root: Annotated[
        Path, typer.Option(help="Output directory for MT5 campaign artifacts.")
    ] = Path("data/processed/mt5_campaigns"),
) -> None:
    """Run local MT5 cached-data campaign review."""
    selected_symbols = [item.strip() for item in symbols.split(",") if item.strip()]
    selected_timeframes = [item.strip() for item in timeframes.split(",") if item.strip()]
    selected_strategies = [item.strip() for item in strategies.split(",") if item.strip()]
    try:
        output_dir = run_mt5_campaign_from_cache(
            cache_dir=cache_dir,
            output_root=output_root,
            broker=broker,
            symbols=selected_symbols,
            timeframes=selected_timeframes,
            strategies=selected_strategies,
            config_snapshot={
                "broker": broker,
                "symbols": selected_symbols,
                "timeframes": selected_timeframes,
                "strategies": selected_strategies,
                "live_trading": False,
                "real_orders_enabled": False,
                "uses_private_api": False,
            },
        )
    except (Mt5ValidationError, Mt5BacktestError, ValueError) as exc:
        console.print(f"[red]MT5 campaign failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]MT5 campaign complete.[/green]")
    console.print(f"artifact path: {output_dir}")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")


@app.command("run-mt5-demo-monitor")
def run_mt5_demo_monitor_command(
    broker: Annotated[str, typer.Option(help="Local cache namespace for the MT5 broker.")] = "mt5",
    symbol: Annotated[str, typer.Option(help="Broker-specific MT5 symbol.")] = "EURUSD",
    timeframe: Annotated[str, typer.Option(help="MT5 timeframe used in cache path.")] = "5m",
    strategy: Annotated[
        str,
        typer.Option(help="NY-session strategy name."),
    ] = "vwap_trend_continuation",
    cache_dir: Annotated[
        Path, typer.Option(help="Local MT5 rates cache directory.")
    ] = Path("data/raw/mt5_rates"),
    state_dir: Annotated[
        Path, typer.Option(help="MT5 demo monitor state directory.")
    ] = Path("data/processed/mt5_demo_monitor"),
    decision_log_dir: Annotated[
        Path, typer.Option(help="MT5 demo monitor decision log directory.")
    ] = Path("data/processed/mt5_demo_monitor/decisions"),
    mt5_config: Annotated[
        Path,
        typer.Option(help="MT5 read-only YAML config for terminal polling."),
    ] = Path("config/mt5_readonly.yaml"),
    source: Annotated[
        str,
        typer.Option(help="Rate source: cached or terminal."),
    ] = "cached",
    bars_count: Annotated[
        int,
        typer.Option(help="Recent terminal bars to request when source=terminal."),
    ] = 300,
    max_iterations: Annotated[int, typer.Option(help="Maximum cached candles to process.")] = 1,
) -> None:
    """Run a bounded MT5 monitor-only check from cached or read-only terminal rates."""
    connector = None
    try:
        if source not in {"cached", "terminal"}:
            raise ValueError("source must be cached or terminal")
        if source == "terminal":
            mt5_module = import_module("MetaTrader5")
            connector = Mt5ReadOnlyConnector(
                load_mt5_readonly_config(mt5_config),
                mt5_module=mt5_module,
            )
            connector.initialize()
            bars = Mt5RatesProvider(mt5_module=mt5_module).fetch_recent_rates(
                symbol=symbol,
                timeframe=timeframe,
                count=bars_count,
            )
        else:
            bars = Mt5RatesCache(cache_dir).read(broker, symbol, timeframe)
        if not bars:
            raise ValueError("missing MT5 rates")
        selected_bars = bars[-max_iterations:]
        state = new_mt5_demo_monitor_state(
            broker=broker,
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy,
        )
        for index in range(len(selected_bars)):
            state = run_mt5_demo_monitor_once(
                state=state,
                bars=bars[: len(bars) - len(selected_bars) + index + 1],
                decision_log_dir=decision_log_dir,
            )
        metadata = {
            "monitor_run_id": state.monitor_run_id,
            "broker": broker,
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy": strategy,
            "live_trading": False,
            "real_orders_enabled": False,
            "uses_private_api": False,
            "demo_execution_requested": False,
            "python_mt5_execution_quarantined": True,
            "source": source,
        }
        Mt5DemoMonitorStore(state_dir).save(state, metadata)
    except (ImportError, Mt5RatesError, Mt5ReadOnlyError, ValueError) as exc:
        console.print(f"[red]MT5 demo monitor failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    finally:
        if connector is not None:
            connector.shutdown()

    console.print("[green]MT5 demo monitor complete.[/green]")
    console.print(f"monitor_run_id: {state.monitor_run_id}")
    console.print(f"decisions: {len(state.decisions)}")
    console.print(f"demo_orders: {len(state.demo_orders)}")
    console.print(f"health_events: {len(state.health_events)}")
    console.print(f"kill_switch_active: {str(state.kill_switch_active).lower()}")
    console.print(f"state path: {Mt5DemoMonitorStore(state_dir).run_dir(state.monitor_run_id)}")
    console.print("python_mt5_execution_quarantined: true")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")


@app.command("install-check")
def install_check_command() -> None:
    """Verify local installation for non-live operation."""
    result = run_install_check()
    console.print(f"install_check: {result['status']}")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")
    if result["status"] != "PASS":
        raise typer.Exit(code=1)


@app.command("final-nonlive-check")
def final_nonlive_check_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
) -> None:
    """Run final non-live release checks."""
    result = run_final_nonlive_check(config)
    console.print(f"final_nonlive_check: {result['status']}")
    if result["status"] == "FAIL":
        raise typer.Exit(code=1)


@app.command("export-human-review-package")
def export_human_review_package_command(
    release_dir: Annotated[
        Path,
        typer.Option(
            "--release-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Release candidate directory.",
        ),
    ],
) -> None:
    """Export the non-live human review package."""
    output_dir = export_human_review_package(release_dir=release_dir)
    console.print("[green]Human review package exported.[/green]")
    console.print(f"output directory: {output_dir}")


@app.command("export-mt5-final-audit-package")
def export_mt5_final_audit_package_command(
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Safety config used for audit."),
    ] = Path("config/default.yaml"),
    mt5_transformation_config: Annotated[
        Path,
        typer.Option(help="MT5 transformation planning config snapshot."),
    ] = Path("config/mt5_transformation.yaml"),
    output_root: Annotated[
        Path,
        typer.Option(help="Output root for MT5 Final Audit Agent packages."),
    ] = Path("data/processed/mt5_final_audits"),
) -> None:
    """Export the MT5 Final Audit Agent review package."""
    try:
        output_dir = export_mt5_final_audit_package(
            config_path=config,
            mt5_transformation_config=mt5_transformation_config,
            output_root=output_root,
        )
    except Mt5FinalAuditPackageError as exc:
        console.print(f"[red]MT5 final audit package failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]MT5 Final Audit Agent package exported.[/green]")
    console.print(f"output directory: {output_dir}")
    console.print("live_trading: false")
    console.print("real_orders_enabled: false")
    console.print("uses_private_api: false")


@app.command("list-profiles")
def list_profiles_command(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/default.yaml"),
) -> None:
    """List config profiles and safety status."""
    for profile in list_profiles(config):
        status = "safety-valid" if profile.safety_valid else "unsafe"
        console.print(
            f"{profile.name}\t{status}\t{profile.description or ''}\t{profile.intended_use or ''}"
        )


@app.command("show-profile")
def show_profile_command(
    profile: Annotated[str, typer.Option(help="Profile name.")],
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("config/default.yaml"),
) -> None:
    """Show merged effective config for a profile."""
    try:
        merged = effective_config(config, profile)
        settings = load_settings(config, profile=profile)
    except (ValidationError, ValueError) as exc:
        console.print("[red]Profile validation failed.[/red]")
        console.print(str(exc))
        raise typer.Exit(code=1) from exc
    console.print(f"safety status: valid mode={settings.mode.value}")
    console.print("warnings: []")
    console.print(dump_effective_config(merged))


@app.command("index-artifacts")
def index_artifacts_command() -> None:
    """Build the local run registry from data/processed artifacts."""
    json_path, jsonl_path = write_registry()
    console.print(f"registry: {json_path}")
    console.print(f"registry jsonl: {jsonl_path}")


@app.command("list-runs")
def list_runs_command(
    run_type: Annotated[str | None, typer.Option("--type", help="Run type filter.")] = None,
) -> None:
    """List indexed or discoverable local runs."""
    entries = load_or_build_registry()
    for entry in entries:
        if run_type is not None and entry["run_type"] != run_type:
            continue
        console.print(f"{entry['run_id']}\t{entry['run_type']}\t{entry['created_at']}\t{entry['path']}")


@app.command("show-run")
def show_run_command(run_id: Annotated[str, typer.Option(help="Run id.")]) -> None:
    """Show metadata and artifacts for a local run."""
    entry = find_run(run_id)
    if entry is None:
        console.print("[red]Run not found.[/red]")
        raise typer.Exit(code=1)
    console.print(format_run(entry))


@app.command("latest-report")
def latest_report_command(
    run_type: Annotated[
        str | None,
        typer.Option("--type", help="Optional report type hint."),
    ] = None,
    open_path: Annotated[bool, typer.Option("--open-path", help="Print local path only.")] = False,
) -> None:
    """Print the latest local report path."""
    path = latest_report(run_type)
    if path is None:
        console.print("[red]No report found.[/red]")
        raise typer.Exit(code=1)
    console.print(path.resolve() if open_path else path)


@app.command("archive-run")
def archive_run_command(run_id: Annotated[str, typer.Option(help="Run id.")]) -> None:
    """Create a zip archive for a run under data/processed."""
    try:
        archive_path, warnings = archive_run(run_id)
    except ValueError as exc:
        console.print(f"[red]Archive failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"archive: {archive_path}")
    for warning in warnings:
        console.print(f"warning: {warning}")


@app.command("print-safe-workflow")
def print_safe_workflow_command() -> None:
    """Print the recommended non-live operator workflow."""
    console.print(safe_workflow())


def fetch_ohlcv_to_cache(
    *,
    provider: MarketDataProvider,
    cache: OhlcvCache,
    exchange: str,
    symbol: str,
    timeframe: str,
    since_days: int,
    limit: int,
    validate_continuity: bool,
    allow_partial_latest_candle: bool,
    now: datetime | None = None,
) -> tuple[int, Path]:
    current_time = (now or datetime.now(UTC)).astimezone(UTC)
    since = current_time - timedelta(days=since_days)
    since_ms = int(since.timestamp() * 1000)
    interval = timeframe_to_timedelta(timeframe)
    fetched = []

    while True:
        batch = provider.fetch_ohlcv(symbol, timeframe, since_ms, limit)
        if not batch:
            break
        fetched.extend(batch)
        newest = max(candle.timestamp for candle in batch)
        since_ms = int((newest + interval).timestamp() * 1000)
        if len(batch) < limit or newest + interval >= current_time:
            break

    if not allow_partial_latest_candle:
        fetched = drop_partial_latest_candle(fetched, timeframe, now=current_time)

    fetched = sorted(fetched, key=lambda candle: candle.timestamp)
    validate_candles(fetched, timeframe, validate_continuity=validate_continuity)
    merged = cache.merge_and_write(exchange, symbol, timeframe, fetched)
    return len(merged), cache.path_for(exchange, symbol, timeframe)


@app.command("fetch-ohlcv")
def fetch_ohlcv(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    exchange: Annotated[str | None, typer.Option(help="Public CCXT exchange id.")] = None,
    symbol: Annotated[str | None, typer.Option(help="Market symbol, for example BTC/USDT.")] = None,
    timeframe: Annotated[str | None, typer.Option(help="OHLCV timeframe, for example 4h.")] = None,
    since_days: Annotated[
        int | None, typer.Option(help="Number of days of history to fetch.")
    ] = None,
) -> None:
    """Fetch public read-only OHLCV candles and write the local cache."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="data", mode=settings.mode.value)

    selected_exchange = exchange or settings.market.exchange
    selected_symbol = symbol or settings.market.symbols[0]
    selected_timeframe = timeframe or settings.market.timeframe
    selected_since_days = since_days or settings.data.since_days

    try:
        provider = CcxtOhlcvProvider(
            selected_exchange,
            timeout_seconds=settings.data.request_timeout_seconds,
            retry_attempts=settings.data.retry_attempts,
            retry_backoff_seconds=settings.data.retry_backoff_seconds,
        )
        rows, cache_path = fetch_ohlcv_to_cache(
            provider=provider,
            cache=OhlcvCache(settings.data.cache_dir),
            exchange=selected_exchange,
            symbol=selected_symbol,
            timeframe=selected_timeframe,
            since_days=selected_since_days,
            limit=settings.data.max_candles_per_request,
            validate_continuity=settings.data.validate_continuity,
            allow_partial_latest_candle=settings.data.allow_partial_latest_candle,
        )
    except (MarketDataError, ValueError) as exc:
        logger.error("fetch_ohlcv_failed", error=str(exc), exchange=selected_exchange)
        console.print(f"[red]OHLCV fetch failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    logger.info(
        "ohlcv_cache_written",
        exchange=selected_exchange,
        symbol=selected_symbol,
        timeframe=selected_timeframe,
        rows=rows,
        cache_path=str(cache_path),
    )
    console.print(f"[green]Cached {rows} candles.[/green] {cache_path}")


@app.command("inspect-data")
def inspect_data(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    exchange: Annotated[str | None, typer.Option(help="Exchange id used in cache path.")] = None,
    symbol: Annotated[str | None, typer.Option(help="Market symbol used in cache path.")] = None,
    timeframe: Annotated[
        str | None, typer.Option(help="OHLCV timeframe used in cache path.")
    ] = None,
) -> None:
    """Inspect cached OHLCV data quality metrics."""
    settings = load_settings(config)
    selected_exchange = exchange or settings.market.exchange
    selected_symbol = symbol or settings.market.symbols[0]
    selected_timeframe = timeframe or settings.market.timeframe

    try:
        report = inspect_cached_data(
            cache_dir=settings.data.cache_dir,
            exchange=selected_exchange,
            symbol=selected_symbol,
            timeframe=selected_timeframe,
        )
    except ValueError as exc:
        configure_logging(mode=settings.mode.value, component="cli")
        logger = get_logger(component="data", mode=settings.mode.value)
        logger.error("inspect_data_failed", error=str(exc), exchange=selected_exchange)
        console.print(f"[red]Data inspection failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    console.print(f"number of candles: {report['rows']}")
    console.print(f"first timestamp: {report['first_timestamp']}")
    console.print(f"last timestamp: {report['last_timestamp']}")
    console.print(f"missing candle count: {report['missing_candle_count']}")
    console.print(f"duplicate count: {report['duplicate_count']}")
    console.print(f"invalid OHLCV row count: {report['invalid_ohlcv_row_count']}")
    console.print(f"latest candle appears incomplete: {report['latest_incomplete']}")
    console.print(f"cache file path: {report['cache_file_path']}")


@app.command("run-backtest")
def run_backtest(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    exchange: Annotated[str | None, typer.Option(help="Exchange id used in cache path.")] = None,
    symbol: Annotated[str | None, typer.Option(help="Market symbol used in cache path.")] = None,
    timeframe: Annotated[
        str | None, typer.Option(help="OHLCV timeframe used in cache path.")
    ] = None,
    strategy: Annotated[str | None, typer.Option(help="Strategy name.")] = None,
) -> None:
    """Run a deterministic local backtest from cached OHLCV data."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="backtest", mode=settings.mode.value)
    selected_exchange = exchange or settings.market.exchange
    selected_symbol = symbol or settings.market.symbols[0]
    selected_timeframe = timeframe or settings.market.timeframe
    selected_strategy_name = strategy or settings.strategy.name

    try:
        selected_strategy = get_strategy(selected_strategy_name, params=settings.strategy.params)
        result = run_backtest_from_cache(
            cache_dir=settings.data.cache_dir,
            output_root=Path("data/processed/backtests"),
            exchange=selected_exchange,
            symbol=selected_symbol,
            timeframe=selected_timeframe,
            strategy=selected_strategy,
            starting_equity=settings.backtesting.starting_equity,
            fee_bps=settings.execution.fee_bps,
            slippage_bps=settings.execution.slippage_bps,
            allow_shorting=settings.backtesting.allow_shorting,
            allow_leverage=settings.backtesting.allow_leverage,
            reject_orders_without_stop=settings.backtesting.reject_orders_without_stop,
            min_cash_pct=settings.backtesting.min_cash_pct,
            risk_per_trade_pct=settings.risk.risk_per_trade_pct,
            max_total_exposure_pct=settings.risk.max_total_exposure_pct,
            min_stop_distance_bps=settings.risk.min_stop_distance_bps,
            max_stop_distance_pct=settings.risk.max_stop_distance_pct,
            mark_to_market=settings.backtesting.mark_to_market,
            config_snapshot=load_yaml(config),
            max_bars=settings.backtesting.max_bars,
        )
    except (BacktestError, ValueError) as exc:
        logger.error("run_backtest_failed", error=str(exc), exchange=selected_exchange)
        console.print(f"[red]Backtest failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    logger.info(
        "backtest_completed",
        run_id=result.run_id,
        strategy=selected_strategy.name,
        final_equity=result.metrics["final_equity"],
    )
    console.print(f"[green]Backtest complete.[/green] run_id={result.run_id}")
    console.print(f"output directory: {result.output_dir}")
    console.print(f"number of trades: {result.metrics['number_of_trades']}")
    console.print(f"total return pct: {result.metrics['total_return_pct']:.4f}")
    console.print(f"max drawdown pct: {result.metrics['max_drawdown_pct']:.4f}")
    console.print(f"fees paid: {result.metrics['fees_paid']:.4f}")
    console.print(f"slippage paid estimate: {result.metrics['slippage_paid_estimate']:.4f}")
    console.print(f"final equity: {result.metrics['final_equity']:.4f}")


@app.command("run-validation")
def run_validation(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    exchange: Annotated[str | None, typer.Option(help="Exchange id used in cache path.")] = None,
    symbol: Annotated[str | None, typer.Option(help="Market symbol used in cache path.")] = None,
    timeframe: Annotated[
        str | None, typer.Option(help="OHLCV timeframe used in cache path.")
    ] = None,
) -> None:
    """Run local out-of-sample and walk-forward validation."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="validation", mode=settings.mode.value)
    selected_exchange = exchange or settings.market.exchange
    selected_symbol = symbol or settings.market.symbols[0]
    selected_timeframe = timeframe or settings.market.timeframe

    try:
        output_dir = run_validation_from_cache(
            settings=settings,
            config_snapshot=load_yaml(config),
            exchange=selected_exchange,
            symbol=selected_symbol,
            timeframe=selected_timeframe,
            output_root=Path("data/processed/validations"),
        )
    except (LocalValidationError, ValueError) as exc:
        logger.error("run_validation_failed", error=str(exc), exchange=selected_exchange)
        console.print(f"[red]Validation failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    logger.info("validation_completed", output_dir=str(output_dir))
    console.print("[green]Validation complete.[/green]")
    console.print(f"output directory: {output_dir}")


class CacheMarketDataProvider:
    def __init__(self, cache: OhlcvCache, exchange: str) -> None:
        self.cache = cache
        self.exchange = exchange

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        limit: int,
    ) -> list[OhlcvCandle]:
        return self.cache.read(self.exchange, symbol, timeframe)[-limit:]


@app.command("run-paper")
def run_paper(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    exchange: Annotated[str | None, typer.Option(help="Public exchange/cache id.")] = None,
    symbol: Annotated[str | None, typer.Option(help="Market symbol.")] = None,
    timeframe: Annotated[str | None, typer.Option(help="OHLCV timeframe.")] = None,
    strategy: Annotated[str | None, typer.Option(help="Strategy name.")] = None,
    max_iterations: Annotated[int | None, typer.Option(help="Maximum loop iterations.")] = None,
    validation_run_id: Annotated[
        str | None, typer.Option(help="Completed validation run id.")
    ] = None,
) -> None:
    """Run public-data paper trading with simulated orders only."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="paper", mode=settings.mode.value)
    if settings.live_trading_enabled or settings.mode.value == "live":
        console.print("[red]Paper trading refuses live-trading configuration.[/red]")
        raise typer.Exit(code=1)
    selected_exchange = exchange or settings.market.exchange
    selected_symbol = symbol or settings.market.symbols[0]
    selected_timeframe = timeframe or settings.market.timeframe
    selected_strategy_name = strategy or settings.strategy.name
    selected_validation_run_id = validation_run_id or settings.paper.validation_run_id

    if settings.paper.require_validation_run:
        if selected_validation_run_id is None:
            console.print("[red]Paper trading requires a completed validation run id.[/red]")
            raise typer.Exit(code=1)
        validation_dir = Path("data/processed/validations") / selected_validation_run_id
        if not validation_dir.exists():
            console.print(
                "[red]Paper trading requires a completed validation run directory.[/red]"
            )
            raise typer.Exit(code=1)

    try:
        provider: MarketDataProvider
        if settings.paper.allow_public_live_data:
            provider = CcxtOhlcvProvider(
                selected_exchange,
                timeout_seconds=settings.data.request_timeout_seconds,
                retry_attempts=settings.data.retry_attempts,
                retry_backoff_seconds=settings.data.retry_backoff_seconds,
            )
        else:
            provider = CacheMarketDataProvider(
                OhlcvCache(settings.data.cache_dir), selected_exchange
            )
        engine = PaperTradingEngine(
            provider=provider,
            execution=SimulatedExecutionClient(
                fee_bps=settings.execution.fee_bps,
                slippage_bps=settings.execution.slippage_bps,
                simulated_latency_ms=settings.paper.simulated_order_latency_ms,
            ),
            store=PaperStateStore(settings.paper.state_dir),
            decision_logger=PaperDecisionLogger(settings.paper.decision_log_dir),
            strategy=get_strategy(selected_strategy_name, params=settings.strategy.params),
            exchange=selected_exchange,
            symbol=selected_symbol,
            timeframe=selected_timeframe,
            starting_equity=settings.paper.starting_equity,
            fee_bps=settings.execution.fee_bps,
            risk_per_trade_pct=settings.risk.risk_per_trade_pct,
            max_total_exposure_pct=settings.risk.max_total_exposure_pct,
            min_stop_distance_bps=settings.risk.min_stop_distance_bps,
            max_stop_distance_pct=settings.risk.max_stop_distance_pct,
            max_consecutive_data_errors=settings.monitoring.max_consecutive_data_errors,
            allow_partial_latest_candle=settings.data.allow_partial_latest_candle,
            resume_existing_state=settings.paper.resume_existing_state,
            persist_state=settings.paper.persist_state,
            validation_run_id=selected_validation_run_id,
        )
        state = engine.run(max_iterations=max_iterations or settings.paper.max_iterations)
    except (PaperTradingError, MarketDataError, ValueError) as exc:
        logger.error("run_paper_failed", error=str(exc), exchange=selected_exchange)
        console.print(f"[red]Paper trading failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    logger.info("paper_run_completed", paper_run_id=state.paper_run_id)
    console.print("[green]Paper run complete.[/green]")
    console.print(f"paper_run_id: {state.paper_run_id}")


@app.command("report-paper")
def report_paper(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    paper_run_id: Annotated[str, typer.Option(help="Paper run id to report on.")] = "",
    validation_run_id: Annotated[str | None, typer.Option(help="Validation run id.")] = None,
    backtest_run_id: Annotated[str | None, typer.Option(help="Backtest run id.")] = None,
) -> None:
    """Generate an auditable paper-trading report."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="reporting", mode=settings.mode.value)
    try:
        if not paper_run_id:
            raise PaperReportError("paper run id is required")
        validation_dir = (
            Path("data/processed/validations") / validation_run_id
            if validation_run_id is not None
            else None
        )
        backtest_dir = (
            Path("data/processed/backtests") / backtest_run_id
            if backtest_run_id is not None
            else None
        )
        output_dir = generate_paper_report(
            paper_run_dir=settings.paper.state_dir / paper_run_id,
            output_root=settings.reporting.output_dir,
            config_snapshot=load_yaml(config),
            readiness_settings=settings.readiness,
            validation_run_dir=validation_dir,
            backtest_run_dir=backtest_dir,
        )
    except (PaperReportError, ValueError) as exc:
        logger.error("report_paper_failed", error=str(exc), paper_run_id=paper_run_id)
        console.print(f"[red]Paper report failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    logger.info("paper_report_written", output_dir=str(output_dir))
    console.print("[green]Paper report complete.[/green]")
    console.print(f"output directory: {output_dir}")


@app.command("run-portfolio-paper")
def run_portfolio_paper(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    exchange: Annotated[str | None, typer.Option(help="Public exchange/cache id.")] = None,
    symbols: Annotated[str | None, typer.Option(help="Comma-separated symbols.")] = None,
    timeframe: Annotated[str | None, typer.Option(help="OHLCV timeframe.")] = None,
    campaign_run_id: Annotated[str | None, typer.Option(help="Campaign run id.")] = None,
    max_iterations: Annotated[int | None, typer.Option(help="Maximum loop iterations.")] = None,
) -> None:
    """Run multi-symbol portfolio paper trading with simulated execution only."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="portfolio_paper", mode=settings.mode.value)
    if settings.mode.value == "live" or settings.live_trading_enabled:
        console.print("[red]Portfolio paper refuses live-trading configuration.[/red]")
        raise typer.Exit(code=1)
    if (
        settings.governance.live_trading_allowed
        or settings.governance.real_orders_allowed
        or settings.governance.private_api_allowed
    ):
        console.print("[red]Portfolio paper refuses unsafe governance configuration.[/red]")
        raise typer.Exit(code=1)

    selected_exchange = exchange or settings.market.exchange
    selected_symbols = _csv(symbols) or settings.portfolio_paper.symbols
    selected_timeframe = timeframe or settings.market.timeframe
    selected_campaign_run_id = campaign_run_id or settings.portfolio_paper.campaign_run_id
    if settings.portfolio_paper.require_campaign_reference:
        if selected_campaign_run_id is None:
            console.print("[red]Portfolio paper requires a completed campaign run id.[/red]")
            raise typer.Exit(code=1)
        campaign_dir = settings.experiments.output_dir / selected_campaign_run_id
        if not campaign_dir.exists():
            console.print("[red]Portfolio paper requires a completed campaign directory.[/red]")
            raise typer.Exit(code=1)

    try:
        strategy_map = {
            symbol: settings.portfolio_paper.strategy_map[symbol] for symbol in selected_symbols
        }
        strategies = {
            symbol: get_strategy(name, params=settings.strategy.params)
            for symbol, name in strategy_map.items()
        }
        provider = CacheMarketDataProvider(OhlcvCache(settings.data.cache_dir), selected_exchange)
        engine = PortfolioPaperTradingEngine(
            provider=provider,
            execution=SimulatedExecutionClient(
                fee_bps=settings.execution.fee_bps,
                slippage_bps=settings.execution.slippage_bps,
                simulated_latency_ms=settings.paper.simulated_order_latency_ms,
            ),
            store=PortfolioPaperStateStore(settings.portfolio_paper.state_dir),
            strategies=strategies,
            portfolio_risk=settings.portfolio_risk,
            exchange=selected_exchange,
            symbols=selected_symbols,
            timeframe=selected_timeframe,
            starting_equity=settings.portfolio_paper.starting_equity,
            fee_bps=settings.execution.fee_bps,
            risk_per_trade_pct=settings.risk.risk_per_trade_pct,
            min_stop_distance_bps=settings.risk.min_stop_distance_bps,
            max_stop_distance_pct=settings.risk.max_stop_distance_pct,
            max_consecutive_data_errors=settings.monitoring.max_consecutive_data_errors,
            allow_partial_latest_candle=settings.data.allow_partial_latest_candle,
            resume_existing_state=settings.portfolio_paper.resume_existing_state,
            persist_state=settings.portfolio_paper.persist_state,
            campaign_run_id=selected_campaign_run_id,
        )
        state = engine.run(
            max_iterations=max_iterations or settings.portfolio_paper.max_iterations
        )
    except (PortfolioPaperTradingError, ValueError, KeyError) as exc:
        logger.error("portfolio_paper_failed", error=str(exc), exchange=selected_exchange)
        console.print(f"[red]Portfolio paper failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    logger.info("portfolio_paper_completed", run_id=state.portfolio_paper_run_id)
    console.print("[green]Portfolio paper run complete.[/green]")
    console.print(f"portfolio_paper_run_id: {state.portfolio_paper_run_id}")


@app.command("report-portfolio-paper")
def report_portfolio_paper(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    portfolio_paper_run_id: Annotated[
        str, typer.Option(help="Portfolio paper run id to report on.")
    ] = "",
) -> None:
    """Generate a portfolio paper-trading report."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="portfolio_reporting", mode=settings.mode.value)
    try:
        if not portfolio_paper_run_id:
            raise PortfolioPaperReportError("portfolio paper run id is required")
        output_dir = generate_portfolio_paper_report(
            state_dir=settings.portfolio_paper.state_dir,
            output_root=settings.reporting.output_dir,
            portfolio_paper_run_id=portfolio_paper_run_id,
            config_snapshot=load_yaml(config),
        )
    except (PortfolioPaperReportError, ValueError) as exc:
        logger.error(
            "portfolio_report_failed", error=str(exc), run_id=portfolio_paper_run_id
        )
        console.print(f"[red]Portfolio report failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    logger.info("portfolio_report_written", output_dir=str(output_dir))
    console.print("[green]Portfolio report complete.[/green]")
    console.print(f"output directory: {output_dir}")


@app.command("run-failure-scenarios")
def run_failure_scenarios_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    scenario: Annotated[str, typer.Option(help="Scenario name or all.")] = "all",
    target: Annotated[str, typer.Option(help="Failure target.")] = "portfolio-paper",
) -> None:
    """Run local simulated failure-injection scenarios."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="failure_injection", mode=settings.mode.value)
    try:
        output_dir = run_failure_scenarios(
            settings=settings,
            config_snapshot=load_yaml(config),
            scenario=scenario,
            target=target,
        )
    except (FailureScenarioError, ValueError) as exc:
        logger.error("failure_scenario_failed", error=str(exc), scenario=scenario)
        console.print(f"[red]Failure scenario failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]Failure scenarios complete.[/green]")
    console.print(f"output directory: {output_dir}")


@app.command("replay-incident")
def replay_incident_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    run_dir: Annotated[
        Path,
        typer.Option(
            "--run-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Run artifact directory to replay.",
        ),
    ] = Path("data/processed/portfolio_paper"),
) -> None:
    """Replay an incident from local artifacts."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="incident_replay", mode=settings.mode.value)
    try:
        output_dir = write_incident_replay(settings=settings, run_dir=run_dir)
    except ValueError as exc:
        logger.error("incident_replay_failed", error=str(exc), run_dir=str(run_dir))
        console.print(f"[red]Incident replay failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]Incident replay complete.[/green]")
    console.print(f"output directory: {output_dir}")


@app.command("run-nonlive-smoke")
def run_nonlive_smoke_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
) -> None:
    """Run the deterministic non-live release smoke workflow."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="release_smoke", mode=settings.mode.value)
    try:
        output_dir = run_nonlive_smoke(settings=settings, config_snapshot=load_yaml(config))
    except ReleaseSmokeError as exc:
        logger.error("release_smoke_failed", error=str(exc))
        console.print(f"[red]Release smoke failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]Non-live release smoke complete.[/green]")
    console.print(f"output directory: {output_dir}")


@app.command("build-release-candidate")
def build_release_candidate_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
) -> None:
    """Build the non-live release candidate package."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="release_package", mode=settings.mode.value)
    try:
        output_dir = build_release_candidate(settings=settings, config_snapshot=load_yaml(config))
    except (ReleasePackageError, ReleaseSmokeError) as exc:
        logger.error("release_package_failed", error=str(exc))
        console.print(f"[red]Release package failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]Release candidate built.[/green]")
    console.print(f"output directory: {output_dir}")


@app.command("verify-release-candidate")
def verify_release_candidate_command(
    release_dir: Annotated[
        Path,
        typer.Option(
            "--release-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Release candidate directory.",
        ),
    ],
) -> None:
    """Verify a non-live release candidate package."""
    try:
        result = verify_release_candidate(release_dir)
    except ReleaseVerificationError as exc:
        console.print(f"[red]Release verification failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print(f"verification: {result['status']}")
    console.print(f"version: {result['version']}")


@app.command("run-safety-audit")
def run_safety_audit_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    include_code: Annotated[bool, typer.Option(help="Include source code scan.")] = True,
    include_config: Annotated[bool, typer.Option(help="Include config scan.")] = True,
    include_env: Annotated[bool, typer.Option(help="Include environment scan.")] = True,
    include_artifacts: Annotated[bool, typer.Option(help="Include artifact scan.")] = True,
) -> None:
    """Run the automated safety audit."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="audit", mode=settings.mode.value)
    try:
        output_dir = run_safety_audit(
            settings=settings,
            include_code=include_code,
            include_config=include_config,
            include_env=include_env,
            include_artifacts=include_artifacts,
        )
    except ValueError as exc:
        logger.error("safety_audit_failed", error=str(exc))
        console.print(f"[red]Safety audit failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]Safety audit complete.[/green]")
    console.print(f"output directory: {output_dir}")


@app.command("write-artifact-manifest")
def write_manifest_command(
    artifact_dir: Annotated[
        Path,
        typer.Option(
            "--artifact-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Artifact directory to hash.",
        ),
    ],
) -> None:
    """Write artifact_manifest.json for a local artifact directory."""
    manifest = write_artifact_manifest(artifact_dir)
    console.print(f"[green]Manifest written.[/green] {manifest}")


@app.command("verify-artifact-manifest")
def verify_manifest_command(
    artifact_dir: Annotated[
        Path,
        typer.Option(
            "--artifact-dir",
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Artifact directory with artifact_manifest.json.",
        ),
    ],
) -> None:
    """Verify artifact_manifest.json for a local artifact directory."""
    result = verify_artifact_manifest(artifact_dir)
    console.print(f"manifest status: {result.status}")
    if result.status == "FAIL":
        raise typer.Exit(code=1)


@app.command("run-campaign")
def run_campaign_command(
    config: Annotated[
        Path,
        typer.Option(
            "--config",
            "-c",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to YAML configuration file.",
        ),
    ] = Path("config/default.yaml"),
    exchange: Annotated[str, typer.Option(help="Exchange/cache id.")] = "sandbox",
    symbols: Annotated[str | None, typer.Option(help="Comma-separated symbols.")] = None,
    timeframes: Annotated[str | None, typer.Option(help="Comma-separated timeframes.")] = None,
    strategies: Annotated[str | None, typer.Option(help="Comma-separated strategies.")] = None,
) -> None:
    """Run fixed-parameter cached-data experiment campaign."""
    settings = load_settings(config)
    configure_logging(mode=settings.mode.value, component="cli")
    logger = get_logger(component="campaign", mode=settings.mode.value)
    try:
        output_dir = run_campaign(
            settings=settings,
            config_snapshot=load_yaml(config),
            exchange=exchange,
            symbols=_csv(symbols),
            timeframes=_csv(timeframes),
            strategies=_csv(strategies),
        )
    except (CampaignError, ValueError) as exc:
        logger.error("campaign_failed", error=str(exc), exchange=exchange)
        console.print(f"[red]Campaign failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    console.print("[green]Campaign complete.[/green]")
    console.print(f"output directory: {output_dir}")


def _csv(value: str | None) -> list[str] | None:
    return [item.strip() for item in value.split(",") if item.strip()] if value else None


if __name__ == "__main__":
    app()
