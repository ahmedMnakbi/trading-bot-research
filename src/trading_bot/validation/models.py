from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChronologicalSplit:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


@dataclass(frozen=True)
class WalkForwardWindow:
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    index: int
