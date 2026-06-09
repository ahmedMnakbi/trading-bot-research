from __future__ import annotations

import pandas as pd


def exponential_moving_average(values: pd.Series, span: int) -> pd.Series:
    if span < 2:
        raise ValueError("span must be at least 2")
    return values.ewm(span=span, adjust=False).mean()

