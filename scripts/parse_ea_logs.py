from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.mql5.log_parser import DEFAULT_OUTPUT_ROOT, parse_ea_logs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Parse monitor-only MQL5 EA logs.")
    parser.add_argument("--log-dir", required=True, help="Directory containing EA logs.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Summary output dir.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = parse_ea_logs(args.log_dir, output_dir=args.output_dir)
    payload = summary.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"ea_log_parse: {summary.status}")
        print(f"summary_json_path: {summary.summary_json_path}")
        print(f"summary_md_path: {summary.summary_md_path}")
        print("Missing logs are handled gracefully and no credentials are required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
