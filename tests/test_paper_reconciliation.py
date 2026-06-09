from __future__ import annotations

from trading_bot.paper.reconciliation import detect_position_mismatch
from trading_bot.paper.state import new_paper_state


def test_paper_reconciliation_detects_position_mismatch() -> None:
    state = new_paper_state(
        exchange="kraken",
        symbol="BTC/USDT",
        timeframe="4h",
        strategy="noop",
        starting_equity=1000,
    )
    state.equity = 900

    assert detect_position_mismatch(state) is True
