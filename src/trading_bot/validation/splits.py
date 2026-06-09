from __future__ import annotations

from trading_bot.validation.models import ChronologicalSplit


def chronological_train_test_split(
    total_bars: int,
    *,
    train_pct: int,
    test_pct: int,
    min_train_bars: int,
    min_test_bars: int,
) -> ChronologicalSplit:
    if train_pct + test_pct != 100:
        raise ValueError("train_pct + test_pct must equal 100")
    train_size = int(total_bars * train_pct / 100)
    test_size = total_bars - train_size
    if train_size < min_train_bars:
        raise ValueError("insufficient train bars")
    if test_size < min_test_bars:
        raise ValueError("insufficient test bars")
    return ChronologicalSplit(
        train_start=0,
        train_end=train_size,
        test_start=train_size,
        test_end=total_bars,
    )

