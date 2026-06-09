from __future__ import annotations

import pytest

from trading_bot.risk.position_sizing import fixed_fractional_position_size


def test_position_sizing_calculates_expected_quantity() -> None:
    result = fixed_fractional_position_size(
        equity=10_000,
        cash=10_000,
        entry_price=100,
        stop_loss=95,
        risk_per_trade_pct=1,
        fee_bps=0,
        max_total_exposure_pct=100,
        min_stop_distance_bps=10,
        max_stop_distance_pct=10,
    )

    assert result.quantity == 20
    assert result.risk_amount == 100


def test_position_sizing_rejects_missing_stop_loss() -> None:
    with pytest.raises(ValueError, match="required"):
        fixed_fractional_position_size(
            equity=10_000,
            cash=10_000,
            entry_price=100,
            stop_loss=None,
            risk_per_trade_pct=1,
            fee_bps=0,
            max_total_exposure_pct=100,
            min_stop_distance_bps=10,
            max_stop_distance_pct=10,
        )


def test_position_sizing_rejects_stop_above_entry_for_long_trade() -> None:
    with pytest.raises(ValueError, match="below"):
        fixed_fractional_position_size(
            equity=10_000,
            cash=10_000,
            entry_price=100,
            stop_loss=101,
            risk_per_trade_pct=1,
            fee_bps=0,
            max_total_exposure_pct=100,
            min_stop_distance_bps=10,
            max_stop_distance_pct=10,
        )


def test_position_sizing_reduces_quantity_when_cash_is_insufficient() -> None:
    result = fixed_fractional_position_size(
        equity=10_000,
        cash=500,
        entry_price=100,
        stop_loss=99,
        risk_per_trade_pct=2,
        fee_bps=0,
        max_total_exposure_pct=100,
        min_stop_distance_bps=10,
        max_stop_distance_pct=10,
    )

    assert result.quantity == 5

