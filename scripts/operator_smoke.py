from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    if Path.cwd().resolve() != root:
        print(f"run this script from repository root: {root}")
        return 1
    commands = [
        [sys.executable, "-m", "trading_bot", "validate-config", "--config", "config/default.yaml"],
        [sys.executable, "scripts/generate_fixture_data.py"],
        [sys.executable, "-m", "trading_bot", "index-artifacts"],
        [sys.executable, "-m", "trading_bot", "list-profiles"],
        [sys.executable, "-m", "trading_bot", "show-profile", "--profile", "research"],
        [
            sys.executable,
            "-m",
            "trading_bot",
            "run-safety-audit",
            "--config",
            "config/default.yaml",
        ],
        [sys.executable, "-m", "trading_bot", "print-safe-workflow"],
    ]
    for command in commands:
        print("==>", " ".join(command))
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
