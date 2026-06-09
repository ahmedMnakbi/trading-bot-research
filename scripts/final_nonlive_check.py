from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_bot.release.final_check import run_final_nonlive_check


def main() -> int:
    result = run_final_nonlive_check()
    print(f"final_nonlive_check: {result['status']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
