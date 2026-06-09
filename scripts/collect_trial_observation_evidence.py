from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

DEFAULT_OUTPUT_ROOT = Path("data/processed/trial_observation")
EVIDENCE_KINDS = (
    "trial_monitor_smoke",
    "formal_trial_observation",
    "strategy_tester",
)
SECRET_NAME_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|credential|login|private|\.env)",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|credential|login)\b\s*[:=]\s*[^\s,;]+"
)
MQL5_SUFFIXES = {".mq5", ".mqh"}
TRIAL_EXECUTION_SOURCE_SUFFIX = "mql5/include/upcomersnysessionpropbot/trialexecution.mqh"


@dataclass(frozen=True)
class EvidenceItem:
    name: str
    status: str
    path: str = ""
    message: str = ""


@dataclass(frozen=True)
class TrialObservationCollectionResult:
    status: str
    run_id: str
    package_dir: str
    manifest_path: str
    evidence_kind: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_trial_observation_evidence(
    *,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    project_root: str | Path = ".",
    run_id: str | None = None,
    evidence_kind: str = "formal_trial_observation",
    ea_logs: str | Path | None = None,
    settings_file: str | Path | None = None,
    compile_log: str | Path | None = None,
    source_scan: str | Path | None = None,
    broker_time_note: str | Path | None = None,
    symbol_session_checklist: str | Path | None = None,
    screenshots_dir: str | Path | None = None,
    no_trial_trades_note: str | Path | None = None,
) -> TrialObservationCollectionResult:
    root = Path(project_root).resolve()
    selected_evidence_kind = (
        evidence_kind if evidence_kind in EVIDENCE_KINDS else "formal_trial_observation"
    )
    selected_run_id = run_id or datetime.now(UTC).strftime("trial_obs_%Y%m%dT%H%M%SZ")
    package_dir = Path(output_root).resolve() / selected_run_id
    package_dir.mkdir(parents=True, exist_ok=True)

    evidence: list[EvidenceItem] = []
    missing: list[str] = []
    skipped: list[str] = []

    evidence.append(
        _copy_optional_path(
            source=source_scan,
            destination=package_dir / "source_scan",
            name="source_scan",
            missing=missing,
            skipped=skipped,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=compile_log,
            destination=package_dir / "compile_log",
            name="compile_log",
            missing=missing,
            skipped=skipped,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=settings_file,
            destination=package_dir / "settings",
            name="settings_file",
            missing=missing,
            skipped=skipped,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=ea_logs,
            destination=package_dir / "ea_monitor_logs",
            name="ea_monitor_logs",
            missing=missing,
            skipped=skipped,
            redact_text=False,
            skip_secret_values=True,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=broker_time_note,
            destination=package_dir / "broker_time_verification",
            name="broker_time_verification",
            missing=missing,
            skipped=skipped,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=symbol_session_checklist,
            destination=package_dir / "symbol_session_verification",
            name="symbol_session_verification",
            missing=missing,
            skipped=skipped,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=screenshots_dir,
            destination=package_dir / "screenshots",
            name="screenshots",
            missing=missing,
            skipped=skipped,
            required=False,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=no_trial_trades_note,
            destination=package_dir / "no_trial_trades",
            name="no_trial_trades_note",
            missing=missing,
            skipped=skipped,
        )
    )

    source_hash_path = package_dir / "source_hashes.json"
    source_hashes = _hash_mql5_source(root / "mql5")
    source_hash_path.write_text(json.dumps(source_hashes, indent=2), encoding="utf-8")
    evidence.append(EvidenceItem("source_hashes", "COLLECTED", str(source_hash_path)))

    order_evidence_path = package_dir / "no_order_placement_evidence.json"
    order_evidence = _build_no_order_placement_evidence(
        root / "mql5",
        root / "src/trading_bot/mql5",
    )
    order_evidence_path.write_text(json.dumps(order_evidence, indent=2), encoding="utf-8")
    evidence.append(
        EvidenceItem(
            "no_order_placement_evidence",
            "COLLECTED" if order_evidence["status"] == "PASS" else "FAIL",
            str(order_evidence_path),
            (
                "order calls absent or isolated to TrialExecution"
                if order_evidence["status"] == "PASS"
                else "disallowed order-call matches found"
            ),
        )
    )

    readme_path = package_dir / "README.md"
    readme_path.write_text(
        _render_readme(selected_run_id, selected_evidence_kind),
        encoding="utf-8",
    )

    manifest = {
        "package_type": "trial_monitor_only_observation_evidence",
        "run_id": selected_run_id,
        "evidence_kind": selected_evidence_kind,
        "smoke_evidence": selected_evidence_kind == "trial_monitor_smoke",
        "formal_trial_evidence": selected_evidence_kind == "formal_trial_observation",
        "strategy_tester_evidence": selected_evidence_kind == "strategy_tester",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "monitor_only": True,
        "trading_approval": False,
        "surge_2_step_blocked": True,
        "vanguard_blocked": True,
        "credentials_collected": False,
        "evidence": [asdict(item) for item in evidence],
        "missing": missing,
        "skipped": skipped,
    }
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    status = "WARN" if missing or skipped else "PASS"
    return TrialObservationCollectionResult(
        status=status,
        run_id=selected_run_id,
        package_dir=str(package_dir),
        manifest_path=str(manifest_path),
        evidence_kind=selected_evidence_kind,
        evidence=evidence,
        missing=missing,
        skipped=skipped,
    )


def _copy_optional_path(
    *,
    source: str | Path | None,
    destination: Path,
    name: str,
    missing: list[str],
    skipped: list[str],
    required: bool = True,
    redact_text: bool = True,
    skip_secret_values: bool = False,
) -> EvidenceItem:
    if source is None:
        if required:
            missing.append(name)
            return EvidenceItem(name, "MISSING", message="path not provided")
        return EvidenceItem(name, "SKIPPED", message="optional path not provided")

    source_path = Path(source)
    if not source_path.exists():
        if required:
            missing.append(name)
            return EvidenceItem(name, "MISSING", str(source_path), "path does not exist")
        return EvidenceItem(name, "SKIPPED", str(source_path), "optional path does not exist")

    if _is_secret_like(source_path):
        skipped.append(name)
        return EvidenceItem(name, "SKIPPED", str(source_path), "secret-like path excluded")

    destination.mkdir(parents=True, exist_ok=True)
    if source_path.is_dir():
        copied = _copy_directory_redacted(
            source_path,
            destination,
            skipped,
            redact_text=redact_text,
            skip_secret_values=skip_secret_values,
        )
    else:
        copied = [
            _copy_file_redacted(
                source_path,
                destination / source_path.name,
                skipped,
                redact_text=redact_text,
                skip_secret_values=skip_secret_values,
            )
        ]
    kept = [path for path in copied if path]
    if not kept and required:
        missing.append(name)
        return EvidenceItem(name, "MISSING", str(destination), "all files were excluded")
    return EvidenceItem(name, "COLLECTED", str(destination), f"files={len(kept)}")


def _copy_directory_redacted(
    source: Path,
    destination: Path,
    skipped: list[str],
    *,
    redact_text: bool,
    skip_secret_values: bool,
) -> list[Path | None]:
    copied: list[Path | None] = []
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        copied.append(
            _copy_file_redacted(
                path,
                destination / relative,
                skipped,
                redact_text=redact_text,
                skip_secret_values=skip_secret_values,
            )
        )
    return copied


def _copy_file_redacted(
    source: Path,
    destination: Path,
    skipped: list[str],
    *,
    redact_text: bool,
    skip_secret_values: bool,
) -> Path | None:
    if _is_secret_like(source):
        skipped.append(str(source))
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    if _is_text_file(source):
        try:
            text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(source, destination)
            return destination
        if skip_secret_values and SECRET_VALUE_RE.search(text):
            skipped.append(str(source))
            return None
        destination.write_text(_redact_text(text) if redact_text else text, encoding="utf-8")
        return destination
    shutil.copy2(source, destination)
    return destination


def _hash_mql5_source(source_root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    if not source_root.exists():
        return hashes
    for path in sorted(source_root.rglob("*")):
        if path.is_file() and path.suffix.lower() in MQL5_SUFFIXES:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes[str(path.relative_to(source_root))] = digest
    return hashes


def _build_no_order_placement_evidence(*roots: Path) -> dict[str, Any]:
    patterns = (
        "OrderSend",
        "CTrade",
        ".Buy(",
        ".Sell(",
        "PositionOpen",
        "BuyLimit",
        "SellLimit",
        "BuyStop",
        "SellStop",
    )
    matches: list[dict[str, Any]] = []
    disallowed_matches: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".mq5", ".mqh", ".py"}:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                for pattern in patterns:
                    if pattern in line:
                        match = {"path": str(path), "line": line_number, "pattern": pattern}
                        matches.append(match)
                        normalized = path.as_posix().lower()
                        if TRIAL_EXECUTION_SOURCE_SUFFIX not in normalized:
                            disallowed_matches.append(match)
    return {
        "status": "PASS" if not disallowed_matches else "FAIL",
        "patterns": patterns,
        "matches": matches,
        "allowed_matches": [
            match for match in matches if match not in disallowed_matches
        ],
        "disallowed_matches": disallowed_matches,
    }


def _is_secret_like(path: Path) -> bool:
    return SECRET_NAME_RE.search(path.name) is not None


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in {
        ".txt",
        ".log",
        ".md",
        ".json",
        ".csv",
        ".set",
        ".ini",
        ".yaml",
        ".yml",
    }


def _redact_text(text: str) -> str:
    return SECRET_VALUE_RE.sub(lambda match: f"{match.group(1)}=<REDACTED>", text)


def _render_readme(run_id: str, evidence_kind: str) -> str:
    return "\n".join(
        [
            "# Trial Monitor-Only Observation Evidence",
            "",
            f"- Run ID: {run_id}",
            f"- Evidence kind: {evidence_kind}",
            "- Monitor-only: true",
            "- Trading approval: false",
            "- Surge 2 Step: blocked",
            "- Vanguard: blocked",
            "- Credentials: not collected",
            "",
            "This package is evidence for review only. It is not approval for Trial trading, "
            "Surge 2 Step, Vanguard, Challenge, Verification, Funded, or live use.",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect local Trial monitor-only EA observation evidence."
    )
    parser.add_argument("--project-root", default=".", help="Repository root.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Output root.")
    parser.add_argument("--run-id", help="Optional deterministic run ID.")
    parser.add_argument(
        "--evidence-kind",
        choices=EVIDENCE_KINDS,
        default="formal_trial_observation",
        help="Classify evidence as smoke, formal Trial observation, or Strategy Tester.",
    )
    parser.add_argument("--ea-logs", help="EA log file or directory supplied by the user.")
    parser.add_argument("--settings-file", help="Safe monitor-only .set file.")
    parser.add_argument("--compile-log", help="MetaEditor compile log.")
    parser.add_argument("--source-scan", help="MQL5 source scan JSON.")
    parser.add_argument("--broker-time-note", help="Broker time verification note.")
    parser.add_argument("--symbol-session-checklist", help="Symbol/session checklist.")
    parser.add_argument("--screenshots-dir", help="Optional screenshots directory.")
    parser.add_argument("--no-trial-trades-note", help="Manual note confirming no Trial trades.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = collect_trial_observation_evidence(
        output_root=args.output_root,
        project_root=args.project_root,
        run_id=args.run_id,
        evidence_kind=args.evidence_kind,
        ea_logs=args.ea_logs,
        settings_file=args.settings_file,
        compile_log=args.compile_log,
        source_scan=args.source_scan,
        broker_time_note=args.broker_time_note,
        symbol_session_checklist=args.symbol_session_checklist,
        screenshots_dir=args.screenshots_dir,
        no_trial_trades_note=args.no_trial_trades_note,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"trial_observation_collection: {result.status}")
        print(f"run_id: {result.run_id}")
        print(f"evidence_kind: {result.evidence_kind}")
        print(f"package_dir: {result.package_dir}")
        if result.missing:
            print("missing: " + ", ".join(result.missing))
        print("No credentials, MT5 login, or trading permissions were used.")
    return 0 if result.status in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
