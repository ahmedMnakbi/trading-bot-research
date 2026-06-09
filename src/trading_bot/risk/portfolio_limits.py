from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from trading_bot.config.settings import PortfolioRiskSettings
from trading_bot.portfolio.portfolio_state import PortfolioPaperState


@dataclass(frozen=True)
class PortfolioRiskDecision:
    accepted: bool
    reason: str = "accepted"
    warnings: list[str] = field(default_factory=list)
    kill_switch: bool = False


def evaluate_portfolio_entry(
    *,
    state: PortfolioPaperState,
    settings: PortfolioRiskSettings,
    symbol: str,
    strategy: str,
    notional: float,
    cash_after: float,
    stop_loss: float | None,
    leverage: float = 1,
    shorting: bool = False,
    new_positions_this_iteration: int = 0,
    correlation: float | None = None,
) -> PortfolioRiskDecision:
    equity = state.equity or state.starting_equity
    if state.kill_switch_active:
        return PortfolioRiskDecision(False, "kill_switch_active", kill_switch=True)
    if stop_loss is None:
        return PortfolioRiskDecision(False, "missing_stop_loss")
    if leverage != 1:
        return PortfolioRiskDecision(False, "leverage_rejected")
    if shorting:
        return PortfolioRiskDecision(False, "shorting_rejected")
    if symbol in state.positions_by_symbol:
        return PortfolioRiskDecision(False, "position_already_exists")
    if len(state.positions_by_symbol) + 1 > settings.max_open_positions:
        return PortfolioRiskDecision(False, "max_open_positions")
    if new_positions_this_iteration + 1 > settings.max_new_positions_per_iteration:
        return PortfolioRiskDecision(False, "max_new_positions_per_iteration")
    if _pct(cash_after, equity) < settings.min_cash_pct:
        return PortfolioRiskDecision(False, "min_cash")

    symbol_exposures, strategy_exposures = _current_exposures(state)
    total_exposure = sum(symbol_exposures.values()) + notional
    symbol_exposure = symbol_exposures.get(symbol, 0) + notional
    strategy_exposure = strategy_exposures.get(strategy, 0) + notional
    if _pct(total_exposure, equity) > settings.max_total_exposure_pct:
        return PortfolioRiskDecision(False, "max_total_exposure")
    if _pct(symbol_exposure, equity) > settings.max_symbol_exposure_pct:
        return PortfolioRiskDecision(False, "max_symbol_exposure")
    if _pct(strategy_exposure, equity) > settings.max_strategy_exposure_pct:
        return PortfolioRiskDecision(False, "max_strategy_exposure")

    if _loss_pct(state.equity, state.starting_equity) >= settings.max_daily_loss_pct:
        return PortfolioRiskDecision(False, "daily_loss_limit")
    if _loss_pct(state.equity, state.starting_equity) >= settings.max_weekly_loss_pct:
        return PortfolioRiskDecision(False, "weekly_loss_limit")
    if _drawdown_pct(state) >= settings.max_drawdown_pct:
        return PortfolioRiskDecision(False, "max_drawdown", kill_switch=True)

    warnings: list[str] = []
    if correlation is not None and correlation >= settings.correlation_warning_threshold:
        if settings.reject_correlated_entries:
            return PortfolioRiskDecision(False, "correlated_entry")
        warnings.append("CORRELATION_WARNING")
    return PortfolioRiskDecision(True, warnings=warnings)


def evaluate_portfolio_health(
    state: PortfolioPaperState, settings: PortfolioRiskSettings
) -> PortfolioRiskDecision:
    if _drawdown_pct(state) >= settings.max_drawdown_pct:
        return PortfolioRiskDecision(False, "max_drawdown", kill_switch=True)
    if _loss_pct(state.equity, state.starting_equity) >= settings.max_daily_loss_pct:
        return PortfolioRiskDecision(False, "daily_loss_limit")
    if _loss_pct(state.equity, state.starting_equity) >= settings.max_weekly_loss_pct:
        return PortfolioRiskDecision(False, "weekly_loss_limit")
    return PortfolioRiskDecision(True)


def _current_exposures(
    state: PortfolioPaperState,
) -> tuple[dict[str, float], dict[str, float]]:
    symbol_exposures: dict[str, float] = {}
    strategy_exposures: dict[str, float] = {}
    for symbol, position in state.positions_by_symbol.items():
        value = position.market_value()
        symbol_exposures[symbol] = value
        strategy_exposures[position.strategy] = strategy_exposures.get(position.strategy, 0) + value
    return symbol_exposures, strategy_exposures


def _pct(value: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return value / denominator * 100


def _loss_pct(equity: float, starting_equity: float) -> float:
    return max(0.0, (starting_equity - equity) / starting_equity * 100)


def _drawdown_pct(state: PortfolioPaperState) -> float:
    values = [state.starting_equity]
    values.extend(float(item["equity"]) for item in state.equity_curve if "equity" in item)
    values.append(state.equity)
    peak = max(values)
    if peak <= 0:
        return 0.0
    return (peak - state.equity) / peak * 100


def mark_kill_switch_if_needed(
    state: PortfolioPaperState,
    settings: PortfolioRiskSettings,
    timestamp: datetime,
) -> PortfolioPaperState:
    decision = evaluate_portfolio_health(state, settings)
    if decision.kill_switch:
        state.kill_switch_active = True
        state.portfolio_warnings.append(f"{timestamp.isoformat()}:{decision.reason}")
    return state
