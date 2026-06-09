from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

AuditStatus = Literal["PASS", "WARN", "FAIL"]


@dataclass
class ScanResult:
    status: AuditStatus
    files_scanned: int = 0
    matches: list[dict[str, object]] = field(default_factory=list)
    allowlisted_matches: list[dict[str, object]] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def combine_status(results: list[ScanResult]) -> AuditStatus:
    if any(result.status == "FAIL" for result in results):
        return "FAIL"
    if any(result.status == "WARN" for result in results):
        return "WARN"
    return "PASS"

