from types import SimpleNamespace

from trading_bot.mt5.demo_execution import (
    LEGACY_NON_PROP_COMPATIBLE_QUARANTINE,
    Mt5DemoExecutionClient,
    Mt5DemoExecutionConfig,
    Mt5DemoOrderRequest,
    load_mt5_demo_execution_config,
)


class FakeMt5:
    ACCOUNT_TRADE_MODE_DEMO = 0
    ACCOUNT_TRADE_MODE_REAL = 2
    TRADE_ACTION_DEAL = 1
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    TRADE_RETCODE_DONE = 10009

    def __init__(self, *, demo: bool = True, spread: int = 10, stop_level: int = 10) -> None:
        self.demo = demo
        self.spread = spread
        self.stop_level = stop_level
        self.check_calls: list[dict[str, object]] = []
        self.send_calls: list[dict[str, object]] = []

    def account_info(self) -> SimpleNamespace:
        return SimpleNamespace(
            trade_mode=(
                self.ACCOUNT_TRADE_MODE_DEMO if self.demo else self.ACCOUNT_TRADE_MODE_REAL
            ),
            server="Demo" if self.demo else "Live",
        )

    def symbol_info(self, symbol: str) -> SimpleNamespace:
        return SimpleNamespace(name=symbol, spread=self.spread, trade_stops_level=self.stop_level)

    def order_check(self, payload: dict[str, object]) -> SimpleNamespace:
        self.check_calls.append(payload)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE)

    def order_send(self, payload: dict[str, object]) -> SimpleNamespace:
        self.send_calls.append(payload)
        return SimpleNamespace(retcode=self.TRADE_RETCODE_DONE, order=123)


def _request() -> Mt5DemoOrderRequest:
    return Mt5DemoOrderRequest(
        symbol="EURUSD",
        side="BUY",
        volume=0.1,
        price=100.0,
        stop_loss=80.0,
        take_profit=130.0,
    )


def test_demo_execution_rejects_when_disabled() -> None:
    mt5 = FakeMt5()
    client = Mt5DemoExecutionClient(mt5, Mt5DemoExecutionConfig(enabled=False))

    result = client.submit_demo_order(_request())

    assert result.accepted is False
    assert result.reason == "demo_execution_disabled"
    assert mt5.send_calls == []


def test_demo_execution_module_is_legacy_quarantined() -> None:
    assert LEGACY_NON_PROP_COMPATIBLE_QUARANTINE is True


def test_demo_execution_config_defaults_are_disabled_and_safe() -> None:
    config = load_mt5_demo_execution_config("config/mt5_demo_execution.yaml")

    assert config.enabled is False
    assert config.demo_only is True
    assert config.live_trading_enabled is False


def test_demo_execution_rejects_live_account() -> None:
    mt5 = FakeMt5(demo=False)
    client = Mt5DemoExecutionClient(mt5, Mt5DemoExecutionConfig(enabled=True))

    result = client.submit_demo_order(_request())

    assert result.accepted is False
    assert result.reason == "live_account_rejected"
    assert mt5.send_calls == []


def test_demo_execution_rejects_unsafe_spread_lot_and_stop() -> None:
    high_spread = Mt5DemoExecutionClient(
        FakeMt5(spread=100),
        Mt5DemoExecutionConfig(enabled=True, max_spread_points=20),
    )
    bad_lot = Mt5DemoExecutionClient(FakeMt5(), Mt5DemoExecutionConfig(enabled=True))
    bad_stop = Mt5DemoExecutionClient(
        FakeMt5(stop_level=30),
        Mt5DemoExecutionConfig(enabled=True, min_stop_distance_points=30),
    )

    assert high_spread.submit_demo_order(_request()).reason == "spread_above_limit"
    assert bad_lot.submit_demo_order(
        Mt5DemoOrderRequest(
            symbol="EURUSD",
            side="BUY",
            volume=0.015,
            price=100.0,
            stop_loss=80.0,
        )
    ).reason == "lot_step_mismatch"
    assert bad_stop.submit_demo_order(_request()).reason == "stop_distance_too_small"


def test_demo_execution_calls_order_check_then_order_send_for_demo_only_order() -> None:
    mt5 = FakeMt5()
    client = Mt5DemoExecutionClient(mt5, Mt5DemoExecutionConfig(enabled=True))

    result = client.submit_demo_order(_request())

    assert result.accepted is True
    assert result.reason == "demo_order_accepted"
    assert result.order == 123
    assert len(mt5.check_calls) == 1
    assert len(mt5.send_calls) == 1
    assert mt5.send_calls[0]["magic"] == 55001
