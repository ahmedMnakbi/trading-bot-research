from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_OUTPUT_ROOT = Path("data/manual_evidence")


@dataclass(frozen=True)
class TrialObservationNotesResult:
    status: str
    run_id: str
    output_dir: str
    files: list[str]
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def create_trial_observation_notes(
    *,
    run_id: str | None = None,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
) -> TrialObservationNotesResult:
    selected_run_id = run_id or datetime.now(UTC).strftime("trial_obs_%Y%m%dT%H%M%SZ")
    output_dir = Path(output_root) / selected_run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "broker_time_note.txt": _broker_time_template(selected_run_id),
        "symbol_session_note.txt": _symbol_session_template(selected_run_id),
        "no_order_no_position_note.txt": _no_order_no_position_template(selected_run_id),
    }
    written: list[str] = []
    for name, text in files.items():
        path = output_dir / name
        path.write_text(text, encoding="utf-8")
        written.append(str(path))

    return TrialObservationNotesResult(
        status="PASS",
        run_id=selected_run_id,
        output_dir=str(output_dir),
        files=written,
        message="Trial monitor-only note templates created",
    )


def _broker_time_template(run_id: str) -> str:
    return "\n".join(
        [
            "Broker Time Verification Note",
            f"Run ID: {run_id}",
            "",
            "Account program: TrialRiskFree",
            "Account stage: Trial or MonitorOnly",
            "Symbol/chart observed:",
            "Observation date/time UTC:",
            "MT5 Market Watch/server time observed:",
            "UTC time observed:",
            "Calculated BrokerServerUtcOffsetMinutes:",
            "New York time comparison:",
            "DST considered: yes/no",
            "Result: broker time offset accepted for this monitor-only observation: yes/no",
            "",
            "Do not include account passwords, investor passwords, API keys, or tokens.",
            "",
        ]
    )


def _symbol_session_template(run_id: str) -> str:
    return "\n".join(
        [
            "Symbol Session Verification Note",
            f"Run ID: {run_id}",
            "",
            "Account program: TrialRiskFree",
            "Symbol/chart observed:",
            "Broker symbol name:",
            "Expected asset class:",
            "Session open/available during observation: yes/no",
            "Spread observed in MT5:",
            "EA spread gate result observed:",
            "Session gate result observed:",
            "Notes on broker naming or session differences:",
            "",
            "Do not include account passwords, investor passwords, API keys, or tokens.",
            "",
        ]
    )


def _no_order_no_position_template(run_id: str) -> str:
    return "\n".join(
        [
            "No Order / No Position Note",
            f"Run ID: {run_id}",
            "",
            "Account program: TrialRiskFree",
            "Symbol/chart observed:",
            "Observation window start/end:",
            "Orders opened: 0",
            "Positions opened: 0",
            "Experts errors observed: none / list below",
            "Journal errors observed: none / list below",
            "Statement: no orders and no positions occurred during this monitor-only run.",
            "",
            "Do not include account passwords, investor passwords, API keys, or tokens.",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create local note templates for formal Trial monitor-only evidence."
    )
    parser.add_argument("--run-id", help="Run ID folder name.")
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Manual evidence root.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = create_trial_observation_notes(
        run_id=args.run_id,
        output_root=args.output_root,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"trial_observation_notes: {result.status}")
        print(f"run_id: {result.run_id}")
        print(f"output_dir: {result.output_dir}")
        for path in result.files:
            print(f"created: {path}")
        print("These notes are monitor-only evidence templates and do not approve trading.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
