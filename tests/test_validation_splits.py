from __future__ import annotations

import pytest

from trading_bot.validation.splits import chronological_train_test_split


def test_static_split_preserves_chronological_order() -> None:
    split = chronological_train_test_split(
        100, train_pct=60, test_pct=40, min_train_bars=1, min_test_bars=1
    )

    assert split.train_start == 0
    assert split.train_end == split.test_start
    assert split.test_end == 100


def test_static_split_uses_correct_train_test_sizes() -> None:
    split = chronological_train_test_split(
        100, train_pct=60, test_pct=40, min_train_bars=1, min_test_bars=1
    )

    assert split.train_end - split.train_start == 60
    assert split.test_end - split.test_start == 40


def test_static_split_rejects_train_pct_plus_test_pct_not_equal_100() -> None:
    with pytest.raises(ValueError, match="100"):
        chronological_train_test_split(
            100, train_pct=70, test_pct=40, min_train_bars=1, min_test_bars=1
        )

