from __future__ import annotations

from collections.abc import Sequence
from importlib import import_module
from pathlib import Path
from typing import Any

from trading_bot.mt5.models import Mt5ReadOnlyConfig, Mt5SymbolInfo, Mt5TerminalStatus
from trading_bot.mt5.safety import assert_mt5_read_only_source
from trading_bot.mt5.symbols import categorize_symbol


class Mt5ReadOnlyError(RuntimeError):
    """Raised when read-only MT5 discovery cannot proceed."""


class Mt5ReadOnlyConnector:
    def __init__(self, config: Mt5ReadOnlyConfig, mt5_module: Any | None = None) -> None:
        self.config = config
        self._mt5 = mt5_module
        self._initialized = False

    @property
    def package_available(self) -> bool:
        try:
            self._module()
        except Mt5ReadOnlyError:
            return False
        return True

    def initialize(self) -> Mt5TerminalStatus:
        assert_mt5_read_only_source(Path("src") / "trading_bot")
        if not self.config.terminal.initialize:
            return Mt5TerminalStatus(
                connected=False,
                package_available=self.package_available,
                terminal_available=False,
            )
        module = self._module()
        kwargs = {}
        if self.config.terminal.path is not None:
            kwargs["path"] = str(self.config.terminal.path)
        try:
            initialized = bool(module.initialize(**kwargs))
        except TypeError:
            initialized = bool(module.initialize())
        if not initialized:
            message = _last_error_message(module)
            raise Mt5ReadOnlyError(f"MT5 terminal initialization failed: {message}")
        self._initialized = True
        return self.terminal_status()

    def terminal_status(self) -> Mt5TerminalStatus:
        module = self._module()
        info = module.terminal_info()
        if info is None:
            return Mt5TerminalStatus(
                connected=self._initialized,
                package_available=True,
                terminal_available=False,
            )
        data = info._asdict() if hasattr(info, "_asdict") else vars(info)
        return Mt5TerminalStatus(
            connected=self._initialized,
            package_available=True,
            terminal_available=True,
            terminal_name=_optional_str(data.get("name")),
            company=_optional_str(data.get("company")),
            server=_optional_str(data.get("server")),
        )

    def discover_symbols(self) -> list[Mt5SymbolInfo]:
        module = self._module()
        raw_symbols = module.symbols_get()
        if raw_symbols is None:
            message = _last_error_message(module)
            raise Mt5ReadOnlyError(f"MT5 symbol discovery failed: {message}")
        selected = _filter_symbols(raw_symbols, self.config.discovery.include_symbols)
        limited = selected[: self.config.discovery.max_symbols]
        return [
            Mt5SymbolInfo.from_mt5(
                raw,
                asset_class=categorize_symbol(
                    str(_raw_value(raw, "name", "")),
                    path=_optional_str(_raw_value(raw, "path", None)),
                ),
            )
            for raw in limited
        ]

    def shutdown(self) -> None:
        if not self._initialized:
            return
        module = self._module()
        shutdown = getattr(module, "shutdown", None)
        if shutdown is not None:
            shutdown()
        self._initialized = False

    def _module(self) -> Any:
        if self._mt5 is not None:
            return self._mt5
        try:
            self._mt5 = import_module("MetaTrader5")
        except ModuleNotFoundError as exc:
            raise Mt5ReadOnlyError(
                "MetaTrader5 package is not installed; install it and use a local MT5 terminal "
                "for read-only discovery."
            ) from exc
        return self._mt5


def _filter_symbols(raw_symbols: Sequence[Any], include_symbols: list[str]) -> list[Any]:
    if not include_symbols:
        return list(raw_symbols)
    requested = {symbol.upper() for symbol in include_symbols}
    return [raw for raw in raw_symbols if str(_raw_value(raw, "name", "")).upper() in requested]


def _raw_value(raw: Any, name: str, default: object) -> object:
    if hasattr(raw, "_asdict"):
        return raw._asdict().get(name, default)
    return getattr(raw, name, default)


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _last_error_message(module: Any) -> str:
    last_error = getattr(module, "last_error", None)
    if last_error is None:
        return "no terminal error detail available"
    try:
        return str(last_error())
    except Exception:
        return "terminal error detail unavailable"
