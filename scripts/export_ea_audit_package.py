from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.mql5.audit_package import (
    DEFAULT_OUTPUT_ROOT,
    export_ea_audit_package,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export a local native MQL5 EA audit package."
    )
    parser.add_argument("--source-scan-path", help="MQL5 source scan JSON path.")
    parser.add_argument("--compile-log-path", help="MetaEditor compile log path.")
    parser.add_argument("--settings-summary-path", help="Generated settings summary JSON path.")
    parser.add_argument(
        "--prop-compliance-report-path",
        help="Prop compliance report JSON path.",
    )
    parser.add_argument("--ea-log-summary-path", help="Optional EA log summary JSON path.")
    parser.add_argument("--trial-evidence-path", help="Optional Trial evidence path.")
    parser.add_argument(
        "--strategy-tester-evidence-path",
        help="Optional Strategy Tester evidence path.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_ROOT), help="Output dir.")
    parser.add_argument("--project-root", default=".", help="Repository root.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = export_ea_audit_package(
        output_dir=args.output_dir,
        source_scan_path=args.source_scan_path,
        compile_log_path=args.compile_log_path,
        settings_summary_path=args.settings_summary_path,
        prop_compliance_report_path=args.prop_compliance_report_path,
        ea_log_summary_path=args.ea_log_summary_path,
        trial_evidence_path=args.trial_evidence_path,
        strategy_tester_evidence_path=args.strategy_tester_evidence_path,
        project_root=args.project_root,
    )
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"ea_audit_package: {result.status}")
        print(f"package_id: {result.package_id}")
        print(f"package_dir: {result.package_dir}")
        print(result.message)
        print("No MT5 login, prop credentials, or trading permissions were used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
