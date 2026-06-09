from __future__ import annotations

from types import SimpleNamespace

import pytest

from trading_bot.mt5.connection import Mt5ReadOnlyConnector
from trading_bot.mt5.models import Mt5AssetClass, Mt5ReadOnlyConfig, Mt5SymbolInfo
from trading_bot.mt5.symbols import categorize_symbol


class NamedObject(SimpleNamespace):
    def _asdict(self) -> dict[str, object]:
        return vars(self)


@pytest.mark.parametrize(
    ("name", "path", "expected"),
    [
        ("EURUSD", "Forex\\Majors", Mt5AssetClass.FOREX),
        ("XAUUSD", "Metals", Mt5AssetClass.GOLD),
        ("US30.cash", "Indices", Mt5AssetClass.INDEX),
        ("BTCUSD", "Crypto", Mt5AssetClass.CRYPTO),
        ("XAGUSD", "Metals", Mt5AssetClass.COMMODITY),
        ("BROKER_CUSTOM", "Synthetic", Mt5AssetClass.UNKNOWN),
    ],
)
def test_symbol_categorization(name: str, path: str, expected: Mt5AssetClass) -> None:
    assert categorize_symbol(name, path=path) == expected


def test_symbol_model_from_mt5_metadata() -> None:
    raw = NamedObject(
        name="EURUSD",
        path="Forex\\Majors",
        description="Euro vs US Dollar",
        visible=True,
        trade_mode=4,
        digits=5,
        point=0.00001,
        spread=12,
        volume_min=0.01,
        volume_step=0.01,
        trade_stops_level=10,
    )

    symbol = Mt5SymbolInfo.from_mt5(raw, asset_class=Mt5AssetClass.FOREX)

    assert symbol.name == "EURUSD"
    assert symbol.asset_class == Mt5AssetClass.FOREX
    assert symbol.visible is True
    assert symbol.volume_min == 0.01
    assert symbol.trade_stops_level == 10


def test_readonly_connector_discovers_symbols_with_mock_mt5() -> None:
    class FakeMt5:
        initialized = False
        shutdown_called = False

        def initialize(self, **kwargs: object) -> bool:
            self.initialized = True
            return True

        def terminal_info(self) -> NamedObject:
            return NamedObject(name="MetaTrader 5", company="Demo Broker", server="Demo")

        def symbols_get(self) -> list[NamedObject]:
            return [
                NamedObject(
                    name="EURUSD",
                    path="Forex\\Majors",
                    description="Euro vs US Dollar",
                    visible=True,
                    trade_mode=4,
                    digits=5,
                    point=0.00001,
                    spread=10,
                    volume_min=0.01,
                    volume_step=0.01,
                    trade_stops_level=10,
                ),
                NamedObject(
                    name="XAUUSD",
                    path="Metals",
                    description="Gold vs US Dollar",
                    visible=True,
                    trade_mode=4,
                    digits=2,
                    point=0.01,
                    spread=25,
                    volume_min=0.01,
                    volume_step=0.01,
                    trade_stops_level=50,
                ),
            ]

        def shutdown(self) -> None:
            self.shutdown_called = True

    fake = FakeMt5()
    connector = Mt5ReadOnlyConnector(Mt5ReadOnlyConfig(), mt5_module=fake)

    status = connector.initialize()
    symbols = connector.discover_symbols()
    connector.shutdown()

    assert status.connected is True
    assert status.terminal_available is True
    assert [symbol.name for symbol in symbols] == ["EURUSD", "XAUUSD"]
    assert symbols[0].asset_class == Mt5AssetClass.FOREX
    assert symbols[1].asset_class == Mt5AssetClass.GOLD
    assert fake.initialized is True
    assert fake.shutdown_called is True
