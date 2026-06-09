from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ReleaseStep:
    name: str
    status: str
    message: str
    artifacts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReleasePackageResult:
    version: str
    output_dir: Path
