from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trading_bot.config.settings import load_settings, load_yaml
from trading_bot.release.smoke import run_nonlive_smoke


def main() -> int:
    config = Path("config/default.yaml")
    output = run_nonlive_smoke(settings=load_settings(config), config_snapshot=load_yaml(config))
    print(f"output directory: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
