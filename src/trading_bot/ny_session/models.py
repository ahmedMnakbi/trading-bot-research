from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NySessionSignal(StrEnum):
    WAIT = "WAIT"
    SETUP_FORMING = "SETUP_FORMING"
    ENTER_LONG = "ENTER_LONG"
    ENTER_SHORT = "ENTER_SHORT"
    SKIP_SPREAD = "SKIP_SPREAD"
    SKIP_NEWS = "SKIP_NEWS"
    EXIT = "EXIT"
    SESSION_CLOSE = "SESSION_CLOSE"


class NySessionSignalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal: NySessionSignal
    reason: str
    stop_loss: float | None = None
    take_profit: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def wait(cls, reason: str, **metadata: Any) -> NySessionSignalResult:
        return cls(signal=NySessionSignal.WAIT, reason=reason, metadata=metadata)

    @classmethod
    def skip_spread(cls, spread: int, max_spread: int) -> NySessionSignalResult:
        return cls(
            signal=NySessionSignal.SKIP_SPREAD,
            reason="spread_above_limit",
            metadata={"spread": spread, "max_spread": max_spread},
        )

    @classmethod
    def skip_news(cls, reason: str = "news_blackout") -> NySessionSignalResult:
        return cls(signal=NySessionSignal.SKIP_NEWS, reason=reason)
