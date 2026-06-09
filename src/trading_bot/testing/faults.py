from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InjectedFault:
    scenario: str
    code: str
    message: str
    severity: str = "WARNING"
