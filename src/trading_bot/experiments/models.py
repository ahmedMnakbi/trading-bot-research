from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ExperimentStatus = Literal["PENDING", "RUNNING", "COMPLETED", "FAILED", "SKIPPED"]
CandidateLabel = Literal["REJECTED", "NEEDS_MORE_DATA", "PAPER_TRADING_CANDIDATE"]


@dataclass
class Experiment:
    experiment_id: str
    exchange: str
    symbol: str
    timeframe: str
    strategy: str
    stages: list[str]
    status: ExperimentStatus = "PENDING"


@dataclass
class ExperimentResult:
    experiment: Experiment
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    candidate_label: CandidateLabel = "NEEDS_MORE_DATA"
    candidate_label_reasons: list[str] = field(default_factory=list)
