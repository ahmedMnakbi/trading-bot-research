from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.mql5.models import ApprovalMetadata
from trading_bot.mql5.settings import (
    STRATEGY_TESTER_ORB_PRESET,
    STRATEGY_TESTER_PRESETS,
    STRATEGY_TESTER_VWAP_PRESET,
    TRIAL_MICRO_EXECUTION_PRESET,
    EaSettingsError,
    generate_settings_artifacts,
)

DEFAULT_OUTPUT = Path("data/processed/ea_settings/trial_monitor_only.set")
TRIAL_MICRO_EXECUTION_OUTPUT = Path(
    "data/processed/ea_settings/trial_risk_free_eurusd_micro_execution.set"
)
STRATEGY_TESTER_OUTPUTS = {
    STRATEGY_TESTER_ORB_PRESET: Path(
        "data/processed/ea_settings/strategy_tester_eurusd_m5_orb.set"
    ),
    STRATEGY_TESTER_VWAP_PRESET: Path(
        "data/processed/ea_settings/strategy_tester_eurusd_m5_vwap.set"
    ),
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate safe execution-disabled MQL5 EA .set files."
    )
    parser.add_argument(
        "--preset",
        choices=[
            TRIAL_MICRO_EXECUTION_PRESET,
            STRATEGY_TESTER_ORB_PRESET,
            STRATEGY_TESTER_VWAP_PRESET,
        ],
        help="Known safe preset to generate.",
    )
    parser.add_argument("--preset-name", default="trial-monitor-only", help="Preset label.")
    parser.add_argument("--output-path", help="Output .set path.")
    parser.add_argument(
        "--account-program",
        default="TrialRiskFree",
        choices=["TrialRiskFree", "Vanguard", "Surge2Step", "Custom"],
        help="Upcomers account program.",
    )
    parser.add_argument(
        "--stage",
        default=None,
        choices=["MonitorOnly", "Trial", "Challenge", "Verification", "Funded"],
        help="EA account stage.",
    )
    parser.add_argument("--account-program-rules-review-id", default="")
    parser.add_argument("--trial-evidence-id", default="")
    parser.add_argument("--source-scan-pass-id", default="")
    parser.add_argument("--compile-pass-id", default="")
    parser.add_argument("--final-audit-package-id", default="")
    parser.add_argument("--human-approval-id", default="")
    parser.add_argument("--prop-day-reset-timezone-confirmation-id", default="")
    parser.add_argument("--dynamic-risk-shield-confirmation-id", default="")
    parser.add_argument(
        "--broker-time-validation-note",
        default="",
        help=(
            "Required for Trial micro-execution after manually verifying "
            "BrokerServerUtcOffsetMinutes."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    preset_name = args.preset or args.preset_name
    output_path = args.output_path
    if output_path is None:
        if preset_name == TRIAL_MICRO_EXECUTION_PRESET:
            output_path = str(TRIAL_MICRO_EXECUTION_OUTPUT)
        elif preset_name in STRATEGY_TESTER_OUTPUTS:
            output_path = str(STRATEGY_TESTER_OUTPUTS[preset_name])
        else:
            output_path = str(DEFAULT_OUTPUT)
    stage = args.stage
    if stage is None:
        stage = "MonitorOnly" if preset_name in STRATEGY_TESTER_PRESETS else "Trial"
    metadata = ApprovalMetadata(
        account_program_rules_review_id=args.account_program_rules_review_id,
        trial_evidence_id=args.trial_evidence_id,
        source_scan_pass_id=args.source_scan_pass_id,
        compile_pass_id=args.compile_pass_id,
        final_audit_package_id=args.final_audit_package_id,
        human_approval_id=args.human_approval_id,
        prop_day_reset_timezone_confirmation_id=args.prop_day_reset_timezone_confirmation_id,
        dynamic_risk_shield_confirmation_id=args.dynamic_risk_shield_confirmation_id,
    )
    try:
        overrides = {}
        if args.broker_time_validation_note:
            overrides["broker_time_validation_note"] = args.broker_time_validation_note
        result = generate_settings_artifacts(
            output_path=output_path,
            preset_name=preset_name,
            account_program=args.account_program,
            stage=stage,
            approval_metadata=metadata,
            overrides=overrides,
        )
    except EaSettingsError as exc:
        if args.json:
            print(json.dumps({"status": "FAIL", "message": str(exc)}, indent=2))
        else:
            print(f"ea_settings: FAIL\n{exc}")
        return 1
    payload = result.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"ea_settings: {result.status}")
        print(f"set_path: {result.set_path}")
        print(f"summary_json_path: {result.summary_json_path}")
        print(f"summary_md_path: {result.summary_md_path}")
        if result.settings.enable_trial_execution:
            print(
                "Trial Risk-Free EURUSD micro-execution is armed in this .set; "
                "disable EnableTrialExecution immediately after first accepted trade "
                "or broker rejection. Python is support-only."
            )
        elif result.settings.strategy_tester_execution_mode:
            print(
                "Strategy Tester simulated execution is armed in this .set; "
                "use it only inside MT5 Strategy Tester. Python is support-only."
            )
        else:
            print("Trading remains disabled; Python is support-only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
