from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.mql5.compliance_report import (
    DEFAULT_OUTPUT_ROOT,
    export_prop_compliance_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export a prop-firm compliance report.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_ROOT), help="Report output dir.")
    parser.add_argument("--source-scan-path", help="Source scan JSON path.")
    parser.add_argument("--compile-log-path", help="MetaEditor compile log path.")
    parser.add_argument("--settings-summary-path", help="Generated settings summary JSON path.")
    parser.add_argument("--log-summary-path", help="Parsed EA log summary JSON path.")
    parser.add_argument("--trial-evidence-path", help="Trial observation evidence path.")
    parser.add_argument(
        "--strategy-tester-evidence-path",
        help="Strategy Tester evidence path.",
    )
    parser.add_argument("--project-root", default=".", help="Repository root.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = export_prop_compliance_report(
        output_dir=args.output_dir,
        source_scan_path=args.source_scan_path,
        compile_log_path=args.compile_log_path,
        settings_summary_path=args.settings_summary_path,
        log_summary_path=args.log_summary_path,
        trial_evidence_path=args.trial_evidence_path,
        strategy_tester_evidence_path=args.strategy_tester_evidence_path,
        project_root=args.project_root,
    )
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"prop_compliance_report: {result.status}")
        print(f"report_json_path: {result.report_json_path}")
        print(f"report_md_path: {result.report_md_path}")
        print("Python remains support-only; protected account programs remain blocked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
