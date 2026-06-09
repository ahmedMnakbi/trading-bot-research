"""Legacy Python MT5 execution quarantine.

This module is retained only for historical non-prop research evidence and old
tests. It is not prop-compatible, must not be imported by prop-firm workflows,
and must never be used for Challenge, Verification, Funded, Surge 2 Step,
Vanguard, or other prop deployment. Native MQL5 EA code is the only
approved prop execution path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml

LEGACY_NON_PROP_COMPATIBLE_QUARANTINE = True


class Mt5DemoExecutionError(RuntimeError):
    """Raised when demo-only MT5 execution rejects a request."""


@dataclass(frozen=True)
class Mt5DemoExecutionConfig:
    enabled: bool = False
    demo_only: bool = True
    live_trading_enabled: bool = False
    max_spread_points: int = 30
    min_stop_distance_points: int = 10
    min_lot: float = 0.01
    lot_step: float = 0.01
    max_lot: float = 1.0
    max_deviation_points: int = 10
    magic_number: int = 55001

    def __post_init__(self) -> None:
        if not self.demo_only or self.live_trading_enabled:
            raise ValueError("MT5 demo execution config refuses live trading")
        if self.min_lot <= 0 or self.lot_step <= 0 or self.max_lot < self.min_lot:
            raise ValueError("invalid MT5 demo lot limits")


@dataclass(frozen=True)
class Mt5DemoOrderRequest:
    symbol: str
    side: Literal["BUY", "SELL"]
    volume: float
    price: float
    stop_loss: float
    take_profit: float | None = None
    comment: str = "trading_bot_demo"


@dataclass(frozen=True)
class Mt5DemoOrderResult:
    accepted: bool
    reason: str
    retcode: int | None = None
    order: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Mt5DemoExecutionClient:
    def __init__(self, mt5_module: Any, config: Mt5DemoExecutionConfig) -> None:
        self._mt5 = mt5_module
        self.config = config

    def submit_demo_order(self, request: Mt5DemoOrderRequest) -> Mt5DemoOrderResult:
        rejection = self._preflight(request)
        if rejection is not None:
            return rejection
        payload = self._order_payload(request)
        check_result = self._mt5.order_check(payload)
        if not _retcode_ok(check_result, self._mt5):
            return Mt5DemoOrderResult(
                accepted=False,
                reason="order_check_rejected",
                retcode=_retcode(check_result),
            )
        result = self._mt5.order_send(payload)
        if not _retcode_ok(result, self._mt5):
            return Mt5DemoOrderResult(
                accepted=False,
                reason="order_send_rejected",
                retcode=_retcode(result),
            )
        return Mt5DemoOrderResult(
            accepted=True,
            reason="demo_order_accepted",
            retcode=_retcode(result),
            order=_optional_int(_value(result, "order")),
            metadata={"demo_only": True, "live_trading": False},
        )

    def _preflight(self, request: Mt5DemoOrderRequest) -> Mt5DemoOrderResult | None:
        if not self.config.enabled:
            return _reject("demo_execution_disabled")
        if not self.config.demo_only or self.config.live_trading_enabled:
            return _reject("live_trading_rejected")
        account = self._mt5.account_info()
        if account is None:
            return _reject("missing_account_info")
        if not _is_demo_account(self._mt5, account):
            return _reject("live_account_rejected")
        symbol = self._mt5.symbol_info(request.symbol)
        if symbol is None:
            return _reject("missing_symbol_info")
        spread = _optional_int(_value(symbol, "spread"))
        if spread is not None and spread > self.config.max_spread_points:
            return _reject("spread_above_limit", spread=spread)
        if request.volume < self.config.min_lot or request.volume > self.config.max_lot:
            return _reject("lot_size_out_of_bounds")
        if not _matches_step(request.volume, self.config.lot_step):
            return _reject("lot_step_mismatch")
        stop_distance = abs(request.price - request.stop_loss)
        min_stop = max(
            float(self.config.min_stop_distance_points),
            float(_optional_int(_value(symbol, "trade_stops_level")) or 0),
        )
        if stop_distance < min_stop:
            return _reject("stop_distance_too_small", stop_distance=stop_distance)
        return None

    def _order_payload(self, request: Mt5DemoOrderRequest) -> dict[str, Any]:
        order_type = (
            self._mt5.ORDER_TYPE_BUY if request.side == "BUY" else self._mt5.ORDER_TYPE_SELL
        )
        return {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": request.symbol,
            "volume": request.volume,
            "type": order_type,
            "price": request.price,
            "sl": request.stop_loss,
            "tp": request.take_profit,
            "deviation": self.config.max_deviation_points,
            "magic": self.config.magic_number,
            "comment": request.comment,
        }


def _is_demo_account(mt5_module: Any, account: Any) -> bool:
    trade_mode = _value(account, "trade_mode")
    demo_constant = getattr(mt5_module, "ACCOUNT_TRADE_MODE_DEMO", None)
    if demo_constant is not None:
        return trade_mode == demo_constant
    server = str(_value(account, "server") or "").lower()
    company = str(_value(account, "company") or "").lower()
    return "demo" in server or "demo" in company


def _retcode_ok(result: Any, mt5_module: Any) -> bool:
    return _retcode(result) == getattr(mt5_module, "TRADE_RETCODE_DONE", 10009)


def _retcode(result: Any) -> int | None:
    return _optional_int(_value(result, "retcode"))


def _reject(reason: str, **metadata: Any) -> Mt5DemoOrderResult:
    return Mt5DemoOrderResult(accepted=False, reason=reason, metadata=metadata)


def _value(raw: Any, name: str) -> Any:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw.get(name)
    if hasattr(raw, "_asdict"):
        return raw._asdict().get(name)
    return getattr(raw, name, None)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _matches_step(volume: float, lot_step: float) -> bool:
    steps = round(volume / lot_step)
    return abs(volume - steps * lot_step) < 1e-9


def load_mt5_demo_execution_config(path: str | Path) -> Mt5DemoExecutionConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("MT5 demo execution config root must be a mapping")
    return Mt5DemoExecutionConfig(**raw)
