from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.mql5.models import Mql5SourceScanReport
from trading_bot.mql5.source_scan import scan_mql5_source_tree


def run_mql5_source_scan(project_root: str | Path = ".") -> Mql5SourceScanReport:
    return scan_mql5_source_tree(project_root)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local static scanning over the MQL5 source tree."
    )
    parser.add_argument("--project-root", default=".", help="Repository root.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument("--output-path", help="Optional JSON artifact output path.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_mql5_source_scan(args.project_root)
    payload = asdict(result)
    if args.output_path:
        output_path = Path(args.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"mql5_source_scan: {result.status}")
        print(f"root: {result.root}")
        print(result.message)
        for violation in result.violations:
            print(f"{violation['path']}:{violation['line']} {violation['pattern']}")
        for check in result.safeguards:
            print(f"{check.status}\t{check.name}\t{check.message}")
        print("No EA trading code is generated or executed by this scan.")
    return 1 if result.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
