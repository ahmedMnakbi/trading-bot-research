from __future__ import annotations

from trading_bot.paper.state import PaperState


def detect_position_mismatch(state: PaperState) -> bool:
    return state.open_position is None and state.equity != state.cash

