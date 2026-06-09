from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_all import Step, ensure_repo_root


def safety_steps() -> list[Step]:
    python = sys.executable
    return [
        Step(
            "python -m trading_bot validate-config --config config/default.yaml",
            (python, "-m", "trading_bot", "validate-config", "--config", "config/default.yaml"),
        ),
        Step(
            "python -m trading_bot run-safety-audit --config config/default.yaml",
            (python, "-m", "trading_bot", "run-safety-audit", "--config", "config/default.yaml"),
        ),
    ]


def latest_audit_report(root: Path | None = None) -> Path | None:
    base = (root or Path.cwd()) / "data/processed/audits"
    if not base.exists():
        return None
    reports = sorted(base.glob("*/report.md"), key=lambda path: path.stat().st_mtime)
    return reports[-1] if reports else None


def run_steps(steps: Sequence[Step]) -> int:
    root = ensure_repo_root()
    for step in steps:
        print(f"==> {step.display}", flush=True)
        result = subprocess.run(step.command, check=False)
        if result.returncode != 0:
            print(f"failed: {step.display}", flush=True)
            report = latest_audit_report(root)
            if report is not None:
                print(f"latest audit report: {report}", flush=True)
            return result.returncode
    report = latest_audit_report(root)
    if report is not None:
        print(f"latest audit report: {report}", flush=True)
    return 0


def main() -> int:
    return run_steps(safety_steps())


if __name__ == "__main__":
    raise SystemExit(main())
