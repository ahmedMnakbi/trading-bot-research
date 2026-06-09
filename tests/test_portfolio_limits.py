from __future__ import annotations

from trading_bot.config.settings import PortfolioRiskSettings
from trading_bot.portfolio.portfolio_state import PortfolioPosition, new_portfolio_paper_state
from trading_bot.risk.portfolio_limits import evaluate_portfolio_entry


def risk(**overrides: object) -> PortfolioRiskSettings:
    data = {
        "max_open_positions": 2,
        "max_total_exposure_pct": 30,
        "max_symbol_exposure_pct": 20,
        "max_strategy_exposure_pct": 25,
        "max_new_positions_per_iteration": 1,
        "min_cash_pct": 5,
        "max_daily_loss_pct": 1,
        "max_weekly_loss_pct": 3,
        "max_drawdown_pct": 10,
        "reject_correlated_entries": False,
        "correlation_warning_threshold": 0.8,
    }
    data.update(overrides)
    return PortfolioRiskSettings.model_validate(data)


def state():
    return new_portfolio_paper_state(
        exchange="kraken",
        timeframe="4h",
        symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        strategy_map={
            "BTC/USDT": "donchian_breakout",
            "ETH/USDT": "ema_trend",
            "SOL/USDT": "ema_trend",
        },
        starting_equity=10_000,
    )


def test_max_open_positions_rejects_excess_entries() -> None:
    item = state()
    item.positions_by_symbol["BTC/USDT"] = PortfolioPosition(
        symbol="BTC/USDT", strategy="donchian_breakout", quantity=1, entry_price=1_000
    )
    item.positions_by_symbol["ETH/USDT"] = PortfolioPosition(
        symbol="ETH/USDT", strategy="ema_trend", quantity=1, entry_price=1_000
    )

    decision = evaluate_portfolio_entry(
        state=item,
        settings=risk(),
        symbol="SOL/USDT",
        strategy="ema_trend",
        notional=500,
        cash_after=9_500,
        stop_loss=90,
    )

    assert not decision.accepted
    assert decision.reason == "max_open_positions"


def test_total_symbol_strategy_and_min_cash_limits_reject_entries() -> None:
    item = state()

    assert not evaluate_portfolio_entry(
        state=item,
        settings=risk(max_total_exposure_pct=5),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=1_000,
        cash_after=9_000,
        stop_loss=90,
    ).accepted
    assert not evaluate_portfolio_entry(
        state=item,
        settings=risk(max_symbol_exposure_pct=5),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=1_000,
        cash_after=9_000,
        stop_loss=90,
    ).accepted
    assert not evaluate_portfolio_entry(
        state=item,
        settings=risk(max_strategy_exposure_pct=5),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=1_000,
        cash_after=9_000,
        stop_loss=90,
    ).accepted
    assert not evaluate_portfolio_entry(
        state=item,
        settings=risk(min_cash_pct=95),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=1_000,
        cash_after=8_000,
        stop_loss=90,
    ).accepted


def test_loss_drawdown_duplicate_stop_short_leverage_and_correlation_rules() -> None:
    item = state()
    item.positions_by_symbol["BTC/USDT"] = PortfolioPosition(
        symbol="BTC/USDT", strategy="donchian_breakout", quantity=1, entry_price=1_000
    )

    assert evaluate_portfolio_entry(
        state=item,
        settings=risk(),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=100,
        cash_after=9_900,
        stop_loss=90,
    ).reason == "position_already_exists"
    assert evaluate_portfolio_entry(
        state=state(),
        settings=risk(),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=100,
        cash_after=9_900,
        stop_loss=None,
    ).reason == "missing_stop_loss"
    assert evaluate_portfolio_entry(
        state=state(),
        settings=risk(),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=100,
        cash_after=9_900,
        stop_loss=90,
        leverage=2,
    ).reason == "leverage_rejected"
    assert evaluate_portfolio_entry(
        state=state(),
        settings=risk(),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=100,
        cash_after=9_900,
        stop_loss=90,
        shorting=True,
    ).reason == "shorting_rejected"

    warning = evaluate_portfolio_entry(
        state=item,
        settings=risk(max_open_positions=3),
        symbol="SOL/USDT",
        strategy="ema_trend",
        notional=100,
        cash_after=9_900,
        stop_loss=90,
        correlation=0.9,
    )
    assert warning.accepted
    assert "CORRELATION_WARNING" in warning.warnings

    rejected = evaluate_portfolio_entry(
        state=item,
        settings=risk(max_open_positions=3, reject_correlated_entries=True),
        symbol="SOL/USDT",
        strategy="ema_trend",
        notional=100,
        cash_after=9_900,
        stop_loss=90,
        correlation=0.9,
    )
    assert rejected.reason == "correlated_entry"


def test_loss_limits_and_drawdown_reject_or_activate_kill_switch() -> None:
    item = state()
    item.equity = 9_800
    assert evaluate_portfolio_entry(
        state=item,
        settings=risk(),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=100,
        cash_after=9_700,
        stop_loss=90,
    ).reason == "daily_loss_limit"

    item.equity = 8_900
    drawdown = evaluate_portfolio_entry(
        state=item,
        settings=risk(max_daily_loss_pct=50, max_weekly_loss_pct=50),
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        notional=100,
        cash_after=8_800,
        stop_loss=90,
    )
    assert drawdown.reason == "max_drawdown"
    assert drawdown.kill_switch
