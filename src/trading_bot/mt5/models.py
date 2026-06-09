from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Mt5AssetClass(StrEnum):
    FOREX = "forex"
    GOLD = "gold"
    INDEX = "index"
    CRYPTO = "crypto"
    COMMODITY = "commodity"
    UNKNOWN = "unknown"


class Mt5SessionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timezone: str = "America/New_York"
    start: str = "08:00"
    end: str = "12:00"


class Mt5DiscoverySettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    include_symbols: list[str] = Field(default_factory=list)
    max_symbols: int = Field(default=200, gt=0)
    categorize_unknown_as: Mt5AssetClass = Mt5AssetClass.UNKNOWN


class Mt5TerminalSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    initialize: bool = True
    path: Path | None = None
    timeout_seconds: int = Field(default=30, gt=0)


class Mt5ReadOnlyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: str = "paper"
    live_trading_enabled: bool = False
    execution_enabled: bool = False
    real_orders_allowed: bool = False
    private_api_allowed: bool = False
    allow_leverage: bool = False
    allow_shorting: bool = False
    terminal: Mt5TerminalSettings = Field(default_factory=Mt5TerminalSettings)
    discovery: Mt5DiscoverySettings = Field(default_factory=Mt5DiscoverySettings)
    session: Mt5SessionSettings = Field(default_factory=Mt5SessionSettings)

    @model_validator(mode="after")
    def enforce_read_only(self) -> Mt5ReadOnlyConfig:
        if self.mode == "live":
            raise ValueError("MT5 read-only config refuses live mode")
        if self.live_trading_enabled:
            raise ValueError("MT5 read-only config requires live_trading_enabled=false")
        if self.execution_enabled:
            raise ValueError("MT5 read-only config requires execution_enabled=false")
        if self.real_orders_allowed:
            raise ValueError("MT5 read-only config requires real_orders_allowed=false")
        if self.private_api_allowed:
            raise ValueError("MT5 read-only config requires private_api_allowed=false")
        if self.allow_leverage:
            raise ValueError("MT5 read-only config requires allow_leverage=false")
        if self.allow_shorting:
            raise ValueError("MT5 read-only config requires allow_shorting=false")
        return self


class Mt5TerminalStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connected: bool
    package_available: bool
    terminal_available: bool
    terminal_name: str | None = None
    company: str | None = None
    server: str | None = None


class Mt5SymbolInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    path: str | None = None
    description: str | None = None
    asset_class: Mt5AssetClass
    visible: bool | None = None
    trade_mode: int | None = None
    digits: int | None = None
    point: float | None = None
    spread: int | None = None
    volume_min: float | None = None
    volume_step: float | None = None
    trade_stops_level: int | None = None

    @classmethod
    def from_mt5(cls, raw: Any, *, asset_class: Mt5AssetClass) -> Mt5SymbolInfo:
        data = raw._asdict() if hasattr(raw, "_asdict") else vars(raw)
        return cls(
            name=str(data.get("name", "")),
            path=_optional_str(data.get("path")),
            description=_optional_str(data.get("description")),
            asset_class=asset_class,
            visible=_optional_bool(data.get("visible")),
            trade_mode=_optional_int(data.get("trade_mode")),
            digits=_optional_int(data.get("digits")),
            point=_optional_float(data.get("point")),
            spread=_optional_int(data.get("spread")),
            volume_min=_optional_float(data.get("volume_min")),
            volume_step=_optional_float(data.get("volume_step")),
            trade_stops_level=_optional_int(data.get("trade_stops_level")),
        )


def load_mt5_readonly_config(path: str | Path) -> Mt5ReadOnlyConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError("MT5 configuration root must be a mapping")
    return Mt5ReadOnlyConfig.model_validate(raw)


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _optional_bool(value: object) -> bool | None:
    return None if value is None else bool(value)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)

