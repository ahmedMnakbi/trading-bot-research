from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_bot.release.verify import verify_release_candidate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--release-dir",
        type=Path,
        default=Path("data/processed/releases/0.1.0-rc1"),
    )
    args = parser.parse_args()
    result = verify_release_candidate(args.release_dir)
    print(f"verification: {result['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
