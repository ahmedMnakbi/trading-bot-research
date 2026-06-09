from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

SECRET_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "PASS", "CREDENTIAL")


@dataclass(frozen=True)
class Step:
    display: str
    command: tuple[str, ...]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_repo_root(cwd: Path | None = None) -> Path:
    current = (cwd or Path.cwd()).resolve()
    root = repo_root()
    if current != root:
        raise SystemExit(f"run this script from the repository root: {root}")
    if not (current / "pyproject.toml").exists() or not (current / "config/default.yaml").exists():
        raise SystemExit("repository root is missing pyproject.toml or config/default.yaml")
    return current


def redacted_environment(env: Mapping[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in env.items():
        if any(marker in key.upper() for marker in SECRET_MARKERS):
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def default_steps() -> list[Step]:
    python = sys.executable
    return [
        Step(
            "python scripts/check_dev_environment.py",
            (python, "scripts/check_dev_environment.py"),
        ),
        Step(
            "python scripts/check_metaeditor.py",
            (python, "scripts/check_metaeditor.py"),
        ),
        Step(
            "python scripts/run_mql5_source_scan.py",
            (python, "scripts/run_mql5_source_scan.py"),
        ),
        Step(
            "python scripts/compile_mql5_ea.py",
            (python, "scripts/compile_mql5_ea.py"),
        ),
        Step(
            "python scripts/run_security_scans.py",
            (python, "scripts/run_security_scans.py"),
        ),
        Step("ruff check .", (python, "-m", "ruff", "check", ".")),
        Step("pytest", (python, "-m", "pytest")),
        Step(
            "python -m trading_bot validate-config --config config/default.yaml",
            (python, "-m", "trading_bot", "validate-config", "--config", "config/default.yaml"),
        ),
        Step(
            "python -m trading_bot run-safety-audit --config config/default.yaml",
            (python, "-m", "trading_bot", "run-safety-audit", "--config", "config/default.yaml"),
        ),
    ]


def run_steps(steps: Sequence[Step]) -> int:
    root = ensure_repo_root()
    env = os.environ.copy()
    temp_parent = root / "tmp" / "check_all"
    temp_parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="pytest_", dir=temp_parent))
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    for step in steps:
        print(f"==> {step.display}", flush=True)
        result = subprocess.run(step.command, check=False, env=env)
        if result.returncode != 0:
            print(f"failed: {step.display}", flush=True)
            return result.returncode
    return 0


def main() -> int:
    return run_steps(default_steps())


if __name__ == "__main__":
    raise SystemExit(main())
