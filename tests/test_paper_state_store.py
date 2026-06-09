from __future__ import annotations

from trading_bot.paper.state import PaperPosition, new_paper_state
from trading_bot.paper.store import PaperStateStore


def test_paper_engine_creates_new_state_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = PaperStateStore(tmp_path)
    state = new_paper_state(
        exchange="kraken",
        symbol="BTC/USDT",
        timeframe="4h",
        strategy="noop",
        starting_equity=1000,
        paper_run_id="paper-test",
    )
    metadata = {"live_trading": False, "real_orders_enabled": False, "uses_private_api": False}
    store.save(state, metadata)

    assert (tmp_path / "paper-test" / "state.json").exists()


def test_paper_state_persists_cash_equity_position_and_last_timestamp(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = PaperStateStore(tmp_path)
    state = new_paper_state(
        exchange="kraken",
        symbol="BTC/USDT",
        timeframe="4h",
        strategy="noop",
        starting_equity=1000,
        paper_run_id="paper-test",
    )
    state.cash = 900
    state.equity = 1005
    state.open_position = PaperPosition(symbol="BTC/USDT", quantity=1, entry_price=100)
    metadata = {"live_trading": False, "real_orders_enabled": False, "uses_private_api": False}
    store.save(state, metadata)
    loaded = store.load("paper-test")

    assert loaded.cash == 900
    assert loaded.equity == 1005
    assert loaded.open_position is not None
