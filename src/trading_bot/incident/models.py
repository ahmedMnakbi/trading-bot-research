from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SafetyOutcome = Literal[
    "SAFE_SHUTDOWN",
    "SAFE_CONTINUATION",
    "UNSAFE_STATE_DETECTED",
    "INSUFFICIENT_ARTIFACTS",
]


@dataclass(frozen=True)
class TimelineEvent:
    timestamp: str
    event_type: str
    source: str
    symbol: str | None
    message: str
    severity: str
