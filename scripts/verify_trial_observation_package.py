from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

RAW_MT5_LOG_RE = re.compile(
    r"\b\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?\b"
)
EDITED_LOG_MARKERS = (
    "cleaned excerpt",
    "edited excerpt",
    "excerpt only",
    "informal excerpt",
    "manual summary",
    "summary only",
    "not raw",
)


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    status: str
    message: str


@dataclass(frozen=True)
class TrialObservationVerificationResult:
    status: str
    package_dir: str
    evidence_kind: str
    checks: list[VerificationCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_trial_observation_package(
    package_dir: str | Path,
) -> TrialObservationVerificationResult:
    root = Path(package_dir)
    checks: list[VerificationCheck] = []
    warnings: list[str] = []
    failures: list[str] = []

    manifest = _read_json(root / "manifest.json")
    evidence_kind = str(manifest.get("evidence_kind") or "formal_trial_observation")
    is_smoke = evidence_kind == "trial_monitor_smoke"
    checks.append(_path_check(root / "manifest.json", "manifest", failures))
    checks.append(_evidence_classification_check(evidence_kind, warnings, failures))
    checks.append(_source_scan_check(root / "source_scan", failures))
    checks.append(_compile_check(root / "compile_log", failures))
    checks.append(_safe_settings_check(root / "settings", failures))
    checks.append(_logs_check(root / "ea_monitor_logs", evidence_kind, warnings, failures))
    checks.append(
        _path_check(
            root / "broker_time_verification",
            "broker_time_verification",
            failures,
            warnings,
            warn_only=is_smoke,
        )
    )
    checks.append(
        _path_check(
            root / "symbol_session_verification",
            "symbol_session_verification",
            failures,
            warnings,
            warn_only=is_smoke,
        )
    )
    checks.append(_path_check(root / "source_hashes.json", "source_hashes", failures))
    checks.append(_no_order_placement_check(root / "no_order_placement_evidence.json", failures))
    checks.append(
        _no_order_no_position_check(root / "no_trial_trades", evidence_kind, warnings, failures)
    )
    checks.append(_credential_check(manifest, failures))

    if failures:
        status = "FAIL"
    elif warnings:
        status = "WARN"
    else:
        status = "PASS"
    return TrialObservationVerificationResult(
        status=status,
        package_dir=str(root),
        evidence_kind=evidence_kind,
        checks=checks,
        warnings=warnings,
        failures=failures,
    )


def _evidence_classification_check(
    evidence_kind: str,
    warnings: list[str],
    failures: list[str],
) -> VerificationCheck:
    if evidence_kind == "formal_trial_observation":
        return VerificationCheck(
            "evidence_classification",
            "PASS",
            "formal Trial observation evidence package",
        )
    if evidence_kind == "trial_monitor_smoke":
        warnings.append("smoke_evidence_only")
        return VerificationCheck(
            "evidence_classification",
            "WARN",
            "smoke evidence only; raw logs and formal Trial observation are still required",
        )
    if evidence_kind == "strategy_tester":
        warnings.append("strategy_tester_evidence_not_trial_observation")
        return VerificationCheck(
            "evidence_classification",
            "WARN",
            "Strategy Tester evidence is separate from Trial monitor-only observation",
        )
    failures.append("evidence_classification")
    return VerificationCheck(
        "evidence_classification",
        "FAIL",
        f"unsupported evidence_kind={evidence_kind}",
    )


def _path_check(
    path: Path,
    name: str,
    failures: list[str],
    warnings: list[str] | None = None,
    *,
    warn_only: bool = False,
) -> VerificationCheck:
    if path.exists() and _has_any_file(path):
        return VerificationCheck(name, "PASS", "evidence present")
    if warn_only:
        if warnings is not None:
            warnings.append(name)
        return VerificationCheck(name, "WARN", "evidence missing for smoke review")
    failures.append(name)
    return VerificationCheck(name, "FAIL", "required evidence missing")


def _source_scan_check(path: Path, failures: list[str]) -> VerificationCheck:
    candidates = _files_under(path)
    for candidate in candidates:
        payload = _read_json(candidate)
        if payload.get("status") == "PASS":
            return VerificationCheck("source_scan_pass", "PASS", str(candidate))
    failures.append("source_scan_pass")
    return VerificationCheck("source_scan_pass", "FAIL", "source scan PASS evidence missing")


def _compile_check(path: Path, failures: list[str]) -> VerificationCheck:
    text = _combined_text(path)
    if "returncode\": 0" in text or "MetaEditor returned 0" in text or '"status": "PASS"' in text:
        return VerificationCheck("compile_pass", "PASS", "compile PASS evidence present")
    failures.append("compile_pass")
    return VerificationCheck("compile_pass", "FAIL", "compile PASS evidence missing")


def _safe_settings_check(path: Path, failures: list[str]) -> VerificationCheck:
    text = _combined_text(path)
    required = (
        "EnableTrading=false",
        "AccountProgram=ACCOUNT_PROGRAM_TRIAL_RISK_FREE",
    )
    if all(item in text for item in required) and "EnablePropChallengeMode=true" not in text:
        return VerificationCheck(
            "safe_settings",
            "PASS",
            "TrialRiskFree monitor-only settings found",
        )
    failures.append("safe_settings")
    return VerificationCheck("safe_settings", "FAIL", "safe Trial monitor-only settings missing")


def _logs_check(
    path: Path,
    evidence_kind: str,
    warnings: list[str],
    failures: list[str],
) -> VerificationCheck:
    text = _combined_text(path)
    lowered = text.lower()
    unsafe_markers = ("ordersend", "trade executed", "position opened", "deal executed")
    if any(marker in lowered for marker in unsafe_markers):
        failures.append("ea_monitor_logs")
        return VerificationCheck(
            "ea_monitor_logs",
            "FAIL",
            "EA logs contain unsafe order/position execution markers",
        )

    has_monitor_marker = "monitor" in lowered or "upcomersnysessionpropbot" in lowered
    has_raw_log_marker = _has_raw_mt5_log_marker(path)
    has_edited_marker = any(marker in lowered for marker in EDITED_LOG_MARKERS)
    if evidence_kind == "formal_trial_observation":
        if text and has_monitor_marker and has_raw_log_marker and not has_edited_marker:
            return VerificationCheck(
                "ea_monitor_logs",
                "PASS",
                "raw monitor-only MT5 logs present",
            )
        failures.append("ea_monitor_logs")
        return VerificationCheck(
            "ea_monitor_logs",
            "FAIL",
            "formal evidence requires raw Experts/Journal or MT5 log files, not edited excerpts",
        )

    if text and has_monitor_marker and not has_edited_marker:
        return VerificationCheck("ea_monitor_logs", "PASS", "monitor logs present")
    warnings.append("ea_monitor_logs")
    return VerificationCheck(
        "ea_monitor_logs",
        "WARN",
        "raw monitor logs missing or not clearly monitor-only; Trial evidence cannot PASS",
    )


def _no_order_placement_check(path: Path, failures: list[str]) -> VerificationCheck:
    payload = _read_json(path)
    if payload.get("status") == "PASS" and not payload.get("disallowed_matches"):
        return VerificationCheck(
            "no_order_placement_evidence",
            "PASS",
            "order calls absent or isolated to TrialExecution",
        )
    failures.append("no_order_placement_evidence")
    return VerificationCheck(
        "no_order_placement_evidence",
        "FAIL",
        "no-order-placement evidence missing or failed",
    )


def _no_order_no_position_check(
    path: Path,
    evidence_kind: str,
    warnings: list[str],
    failures: list[str],
) -> VerificationCheck:
    text = _combined_text(path).lower()
    if (
        ("no orders" in text and "no positions" in text)
        or ("orders opened: 0" in text and "positions opened: 0" in text)
        or "no order placement and no positions" in text
    ):
        return VerificationCheck(
            "no_order_no_position",
            "PASS",
            "manual no-order/no-position note present",
        )
    if evidence_kind == "formal_trial_observation":
        failures.append("no_order_no_position")
        return VerificationCheck(
            "no_order_no_position",
            "FAIL",
            "formal evidence requires a manual no-order/no-position note",
        )
    warnings.append("no_order_no_position")
    return VerificationCheck(
        "no_order_no_position",
        "WARN",
        "manual no-order/no-position note missing",
    )


def _credential_check(manifest: dict[str, Any], failures: list[str]) -> VerificationCheck:
    if manifest.get("credentials_collected") is False:
        return VerificationCheck("credentials_not_collected", "PASS", "manifest says false")
    failures.append("credentials_not_collected")
    return VerificationCheck(
        "credentials_not_collected",
        "FAIL",
        "manifest missing credentials_collected=false",
    )


def _files_under(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return [item for item in path.rglob("*") if item.is_file()]
    return []


def _has_any_file(path: Path) -> bool:
    return bool(_files_under(path))


def _has_raw_mt5_log_marker(path: Path) -> bool:
    for item in _files_under(path):
        try:
            text = item.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if RAW_MT5_LOG_RE.search(text):
            return True
    return False


def _combined_text(path: Path) -> str:
    parts: list[str] = []
    for item in _files_under(path):
        try:
            parts.append(item.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
    return "\n".join(parts)


def _read_json(path: Path) -> dict[str, Any]:
    if path.is_dir():
        for item in _files_under(path):
            if item.suffix.lower() == ".json":
                try:
                    return json.loads(item.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify a local Trial monitor-only observation evidence package."
    )
    parser.add_argument(
        "package_dir",
        help="Package directory under data/processed/trial_observation.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = verify_trial_observation_package(args.package_dir)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"trial_observation_verification: {result.status}")
        print(f"package_dir: {result.package_dir}")
        print(f"evidence_kind: {result.evidence_kind}")
        if result.warnings:
            print("warnings: " + ", ".join(result.warnings))
        if result.failures:
            print("failures: " + ", ".join(result.failures))
        print("Verification is monitor-only and does not approve trading.")
    return 1 if result.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
