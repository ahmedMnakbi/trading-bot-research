from __future__ import annotations

import pytest

from trading_bot.validation.walk_forward import create_walk_forward_windows


def test_walk_forward_creates_expected_windows() -> None:
    windows = create_walk_forward_windows(900, train_bars=500, test_bars=125, step_bars=125)

    assert len(windows) == 3
    assert windows[0].train_start == 0
    assert windows[0].test_start == 500
    assert windows[1].train_start == 125
    assert windows[2].test_end == 875


def test_walk_forward_rejects_insufficient_data() -> None:
    with pytest.raises(ValueError, match="insufficient"):
        create_walk_forward_windows(100, train_bars=80, test_bars=40, step_bars=10)


def test_walk_forward_does_not_modify_strategy_parameters() -> None:
    params = {"donchian_lookback": 20}
    _ = create_walk_forward_windows(900, train_bars=500, test_bars=125, step_bars=125)

    assert params == {"donchian_lookback": 20}

