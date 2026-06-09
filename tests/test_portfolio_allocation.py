from __future__ import annotations

from trading_bot.portfolio.allocation import plan_allocation


def test_allocation_plan_accounts_for_fee() -> None:
    plan = plan_allocation(
        symbol="BTC/USDT",
        strategy="donchian_breakout",
        quantity=1,
        price=100,
        cash=1_000,
        fee_bps=10,
    )

    assert plan.notional == 100
    assert plan.cash_after == 899.9
