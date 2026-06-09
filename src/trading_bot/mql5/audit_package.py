from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_bot.mql5.models import to_jsonable
from trading_bot.mql5.source_scan import scan_mql5_source_tree

DEFAULT_OUTPUT_ROOT = Path("data/processed/ea_audit_packages")
PACKAGE_TYPE = "native_mql5_ea_audit"
ACCOUNT_PROGRAMS_SUPPORTED = ["TrialRiskFree", "Surge2Step", "Vanguard", "Custom"]
SOURCE_SUFFIXES = {".mq5", ".mqh"}
DOC_SUFFIXES = {".md"}
SENSITIVE_KEY_RE = re.compile(
    r"(?i)\b(api[_-]?key|se"
    r"cret|token|pass"
    r"word|credential|login|account_number)\b"
)
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|se"
    r"cret|token|pass"
    r"word|credential|login|account_number)"
    r"\b\s*[:=]\s*([^\s,;]+)"
)
ORDER_CALL_RE = re.compile(
    r"(?i)(\bOrder"
    r"Send\s*\(|\bC"
    r"Trade\b|\."
    r"Buy\s*\(|\."
    r"Sell\s*\(|\bPosition"
    r"Open\s*\()"
)
PROHIBITED_PATTERN_NAMES = {
    "grid_trading",
    "martingale",
    "averaging_down",
    "hft",
    "arbitrage",
    "copy_trading",
    "sub_2_minute_scalping",
    "tick_scalping",
}
DOC_FILES = [
    Path("README.md"),
    Path("SAFETY.md"),
    Path("AGENTS.md"),
    Path("docs"),
]


@dataclass(frozen=True)
class EaAuditPackageArtifacts:
    status: str
    package_id: str
    package_dir: str
    manifest_path: str
    audit_summary_path: str
    evidence_status_path: str
    known_blockers_path: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return to_jsonable(self)


def export_ea_audit_package(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_ROOT,
    source_scan_path: str | Path | None = None,
    compile_log_path: str | Path | None = None,
    settings_summary_path: str | Path | None = None,
    prop_compliance_report_path: str | Path | None = None,
    ea_log_summary_path: str | Path | None = None,
    trial_evidence_path: str | Path | None = None,
    strategy_tester_evidence_path: str | Path | None = None,
    project_root: str | Path = ".",
    package_id: str | None = None,
) -> EaAuditPackageArtifacts:
    root = Path(project_root).resolve()
    created_at = datetime.now(UTC).isoformat()
    resolved_package_id = package_id or _new_package_id()
    package_root = _resolve_output_dir(root, output_dir) / resolved_package_id
    package_root.mkdir(parents=True, exist_ok=False)

    reports_dir = package_root / "reports"
    reports_dir.mkdir()
    docs_snapshot = package_root / "docs_snapshot"
    mql5_snapshot = package_root / "mql5_source_snapshot"
    docs_snapshot.mkdir()
    mql5_snapshot.mkdir()

    source_scan = _source_scan_payload(root, source_scan_path)
    compile_summary = _compile_summary(compile_log_path)
    settings_summary = _settings_summary(settings_summary_path)
    prop_compliance_summary = _prop_compliance_summary(prop_compliance_report_path)
    ea_log_summary = _read_json_optional(ea_log_summary_path)

    source_files = list(_iter_mql5_source_files(root / "mql5"))
    source_hashes = _source_hashes(root, source_files)
    source_evidence = _source_evidence(
        source_files=source_files,
        source_scan=source_scan,
    )
    compile_evidence = _compile_evidence(compile_summary)
    settings_evidence = _settings_evidence(settings_summary)
    compliance_evidence = _compliance_evidence(prop_compliance_summary)
    missing_evidence = _missing_evidence(
        ea_log_summary_path=ea_log_summary_path,
        ea_log_summary=ea_log_summary,
        trial_evidence_path=trial_evidence_path,
        strategy_tester_evidence_path=strategy_tester_evidence_path,
    )
    evidence_status = {
        "source_evidence": source_evidence,
        "compile_evidence": compile_evidence,
        "settings_evidence": settings_evidence,
        "compliance_evidence": compliance_evidence,
        "missing_evidence": missing_evidence,
    }
    known_blockers = _known_blockers(evidence_status)
    metadata = _metadata(resolved_package_id, created_at)
    audit_summary = _audit_summary(metadata, evidence_status, known_blockers)
    manifest = _manifest(metadata, package_root, evidence_status, known_blockers)

    _write_json(package_root / "package_manifest.json", manifest)
    _write_json(package_root / "audit_summary.json", audit_summary)
    _write_json(package_root / "source_hashes.json", source_hashes)
    _write_json(package_root / "mql5_source_scan.json", source_scan)
    _write_json(package_root / "compile_summary.json", compile_summary)
    _write_json(package_root / "settings_summary.json", settings_summary)
    _write_json(package_root / "prop_compliance_summary.json", prop_compliance_summary)
    _write_json(package_root / "evidence_status.json", evidence_status)
    _write_json(package_root / "known_blockers.json", known_blockers)
    (package_root / "README.md").write_text(
        _render_readme(audit_summary),
        encoding="utf-8",
    )
    (reports_dir / "audit_summary.md").write_text(
        _render_readme(audit_summary),
        encoding="utf-8",
    )

    _copy_docs_snapshot(root, docs_snapshot)
    _copy_mql5_snapshot(root, mql5_snapshot)
    _copy_report_inputs(
        reports_dir=reports_dir,
        paths=[
            source_scan_path,
            compile_log_path,
            settings_summary_path,
            prop_compliance_report_path,
            ea_log_summary_path,
            trial_evidence_path,
            strategy_tester_evidence_path,
        ],
    )

    status = "SOURCE_REVIEW_READY_WITH_BLOCKERS"
    if not source_evidence["complete"] or not compile_evidence["compile_log_present"]:
        status = "INCOMPLETE_FOR_SOURCE_REVIEW"
    return EaAuditPackageArtifacts(
        status=status,
        package_id=resolved_package_id,
        package_dir=str(package_root),
        manifest_path=str(package_root / "package_manifest.json"),
        audit_summary_path=str(package_root / "audit_summary.json"),
        evidence_status_path=str(package_root / "evidence_status.json"),
        known_blockers_path=str(package_root / "known_blockers.json"),
        message="native MQL5 EA audit package exported; trading remains blocked",
    )


def _new_package_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"ea_audit_{timestamp}_{uuid4().hex[:8]}"


def _resolve_output_dir(root: Path, output_dir: str | Path) -> Path:
    candidate = Path(output_dir)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _metadata(package_id: str, created_at: str) -> dict[str, Any]:
    return {
        "package_id": package_id,
        "created_at": created_at,
        "package_type": PACKAGE_TYPE,
        "prop_firm": "Upcomers",
        "account_programs_supported": ACCOUNT_PROGRAMS_SUPPORTED,
        "first_testing_account": "TrialRiskFree",
        "surge2step_rule_verified": False,
        "vanguard_rule_verified": False,
        "native_mql5_ea_execution_path": True,
        "python_prop_execution_allowed": False,
        "trading_enabled_by_default": False,
        "trial_approved_for_trading": False,
        "surge_approved_for_trading": False,
        "vanguard_approved_for_trading": False,
        "challenge_use_approved": False,
        "live_trading_approved": False,
        "monitor_only_phase": True,
    }


def _manifest(
    metadata: dict[str, Any],
    package_root: Path,
    evidence_status: dict[str, Any],
    known_blockers: dict[str, Any],
) -> dict[str, Any]:
    return {
        **metadata,
        "status": "SOURCE_REVIEW_READY_WITH_BLOCKERS",
        "evidence_complete": False,
        "blocker_count": len(known_blockers["blockers"]),
        "package_root": str(package_root),
        "required_files": [
            "package_manifest.json",
            "audit_summary.json",
            "source_hashes.json",
            "mql5_source_scan.json",
            "compile_summary.json",
            "settings_summary.json",
            "prop_compliance_summary.json",
            "evidence_status.json",
            "known_blockers.json",
            "docs_snapshot/",
            "mql5_source_snapshot/",
            "reports/",
            "README.md",
        ],
        "evidence_status": evidence_status,
    }


def _audit_summary(
    metadata: dict[str, Any],
    evidence_status: dict[str, Any],
    known_blockers: dict[str, Any],
) -> dict[str, Any]:
    return {
        **metadata,
        "status": "SOURCE_REVIEW_READY_WITH_BLOCKERS",
        "honesty_statement": (
            "This package is for source, compile, settings, and manual install review. "
            "It is not approval for Trial trading, Surge 2 Step, Vanguard, Challenge, "
            "Verification, Funded, live money, or profitability claims."
        ),
        "may_be_used_for": [
            "source review",
            "compile review",
            "manual install review",
            "Trial monitor-only testing only after before-trial blockers are resolved "
            "or explicitly accepted",
        ],
        "not_approved_for": [
            "Trial trading",
            "Surge 2 Step trading",
            "Vanguard trading",
            "Challenge use",
            "Verification use",
            "Funded use",
            "live money",
            "profitability claims",
        ],
        "evidence_status": evidence_status,
        "known_blockers": known_blockers["blockers"],
    }


def _source_scan_payload(root: Path, source_scan_path: str | Path | None) -> dict[str, Any]:
    payload = _read_json_optional(source_scan_path)
    if payload is not None:
        return payload
    payload = scan_mql5_source_tree(root).to_dict()
    payload["generated_inside_audit_package"] = True
    return payload


def _compile_summary(compile_log_path: str | Path | None) -> dict[str, Any]:
    if compile_log_path is None:
        return {
            "status": "MISSING",
            "compile_log_path": "",
            "message": "compile log path not supplied",
        }
    path = Path(compile_log_path)
    if not path.exists():
        return {
            "status": "MISSING",
            "compile_log_path": str(path),
            "message": "compile log unavailable",
        }
    text = _redact_text(path.read_text(encoding="utf-8", errors="ignore"))
    lowered = text.lower()
    if "skipped" in lowered:
        status = "SKIPPED"
    elif "returned 0" in lowered or "0 error" in lowered:
        status = "PASS"
    elif "returned" in lowered or "error" in lowered:
        status = "FAIL"
    else:
        status = "PRESENT_REVIEW_REQUIRED"
    return {
        "status": status,
        "compile_log_path": str(path),
        "message": "compile log loaded",
        "log_excerpt": text[:2000],
    }


def _settings_summary(settings_summary_path: str | Path | None) -> dict[str, Any]:
    payload = _read_json_optional(settings_summary_path)
    if payload is None:
        return {
            "status": "MISSING",
            "settings_summary_path": str(settings_summary_path or ""),
            "message": "settings summary unavailable",
        }
    payload["settings_summary_path"] = str(settings_summary_path)
    return _redact_payload(payload)


def _prop_compliance_summary(prop_compliance_report_path: str | Path | None) -> dict[str, Any]:
    payload = _read_json_optional(prop_compliance_report_path)
    if payload is None:
        return {
            "status": "MISSING",
            "prop_compliance_report_path": str(prop_compliance_report_path or ""),
            "message": "prop compliance report unavailable",
        }
    payload["prop_compliance_report_path"] = str(prop_compliance_report_path)
    return _redact_payload(payload)


def _source_evidence(
    *,
    source_files: list[Path],
    source_scan: dict[str, Any],
) -> dict[str, Any]:
    order_matches = _find_order_call_matches(source_files)
    violations = source_scan.get("violations") or []
    prohibited = [
        violation
        for violation in violations
        if violation.get("pattern") in PROHIBITED_PATTERN_NAMES
    ]
    source_scan_pass = source_scan.get("status") == "PASS"
    complete = bool(source_files) and source_scan_pass and not order_matches and not prohibited
    return {
        "mql5_source_present": bool(source_files),
        "source_scan_pass": source_scan_pass,
        "no_order_placement_calls": not order_matches,
        "order_call_matches": order_matches,
        "no_prohibited_strategy_patterns": not prohibited,
        "prohibited_strategy_matches": prohibited,
        "complete": complete,
    }


def _compile_evidence(compile_summary: dict[str, Any]) -> dict[str, Any]:
    status = compile_summary.get("status", "MISSING")
    return {
        "metaeditor_compile_status": status,
        "compile_log_path": compile_summary.get("compile_log_path", ""),
        "compile_log_present": status in {"PASS", "FAIL", "SKIPPED", "PRESENT_REVIEW_REQUIRED"},
        "compile_pass": status == "PASS",
        "complete": status == "PASS",
    }


def _settings_evidence(settings_summary: dict[str, Any]) -> dict[str, Any]:
    settings = settings_summary.get("settings") or {}
    account_program = settings_summary.get("account_program") or settings.get("account_program")
    account_stage = settings_summary.get("account_stage") or settings.get("account_stage")
    trading_enabled = bool(
        settings_summary.get("trading_enabled", settings.get("enable_trading", True))
    )
    prop_mode = bool(
        settings_summary.get(
            "prop_challenge_mode",
            settings.get("enable_prop_challenge_mode", True),
        )
    )
    trial_monitor_only = (
        account_program == "TrialRiskFree"
        and account_stage in {"Trial", "MonitorOnly"}
        and bool(settings_summary.get("monitor_only", False))
    )
    return {
        "trial_monitor_only_set_generated": trial_monitor_only,
        "account_program": account_program or "",
        "account_stage": account_stage or "",
        "trading_disabled": not trading_enabled,
        "prop_challenge_mode_disabled": not prop_mode,
        "complete": trial_monitor_only and not trading_enabled and not prop_mode,
    }


def _compliance_evidence(prop_compliance_summary: dict[str, Any]) -> dict[str, Any]:
    mapping = prop_compliance_summary.get("upcomers_rule_mapping") or {}
    safety = prop_compliance_summary.get("safety_statements") or {}
    daily = mapping.get("daily_loss_limit") or {}
    overall = mapping.get("overall_loss_limit") or {}
    generated = prop_compliance_summary.get("status") != "MISSING"
    return {
        "prop_compliance_report_generated": generated,
        "upcomers_limits_mapped_where_verified": bool(daily and overall),
        "stricter_internal_limits_documented": (
            daily.get("ea_hard_limit") == "3%" and overall.get("ea_hard_limit") == "6%"
        ),
        "surge_exact_rules_unverified": bool(safety.get("surge_2_step_rule_unverified", True)),
        "vanguard_exact_rules_unverified": bool(safety.get("vanguard_blocked", True)),
        "complete": generated and bool(daily and overall),
    }


def _missing_evidence(
    *,
    ea_log_summary_path: str | Path | None,
    ea_log_summary: dict[str, Any] | None,
    trial_evidence_path: str | Path | None,
    strategy_tester_evidence_path: str | Path | None,
) -> dict[str, Any]:
    monitor_logs_present = (
        ea_log_summary is not None
        and ea_log_summary.get("status") == "PASS"
        and int(ea_log_summary.get("files_scanned") or 0) > 0
    )
    return {
        "real_monitor_only_ea_logs_missing": not monitor_logs_present,
        "real_monitor_only_ea_logs_path": str(ea_log_summary_path or ""),
        "trial_observation_evidence_missing": not _path_has_evidence(trial_evidence_path),
        "trial_evidence_path": str(trial_evidence_path or ""),
        "strategy_tester_evidence_missing": not _path_has_evidence(
            strategy_tester_evidence_path
        ),
        "strategy_tester_evidence_path": str(strategy_tester_evidence_path or ""),
        "daily_reset_timezone_unconfirmed": True,
        "dynamic_risk_shield_exact_calculation_unconfirmed": True,
        "surge_2_step_exact_rule_review_missing": True,
        "vanguard_exact_rule_review_missing": True,
        "human_approval_metadata_missing": True,
        "final_audit_agent_review_missing": True,
        "complete": False,
    }


def _known_blockers(evidence_status: dict[str, Any]) -> dict[str, Any]:
    blockers = [
        "real monitor-only EA logs missing until the user runs the EA on Trial",
        "Trial observation evidence missing",
        "Strategy Tester evidence missing",
        "daily reset timezone unconfirmed",
        "Dynamic Risk Shield exact calculation unconfirmed",
        "Surge 2 Step exact rule review missing",
        "Vanguard exact rule review missing",
        "human approval metadata missing",
        "Final Audit Agent review missing",
    ]
    if not evidence_status["source_evidence"]["complete"]:
        blockers.append("source evidence incomplete")
    if not evidence_status["compile_evidence"]["complete"]:
        blockers.append("compile evidence not PASS")
    if not evidence_status["settings_evidence"]["complete"]:
        blockers.append("Trial/MonitorOnly settings evidence incomplete")
    if not evidence_status["compliance_evidence"]["complete"]:
        blockers.append("prop compliance evidence incomplete")
    return {"blockers": blockers, "blocker_count": len(blockers)}


def _source_hashes(root: Path, source_files: list[Path]) -> dict[str, Any]:
    entries = []
    for path in source_files:
        entries.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    support_sources = [
        path
        for path in (root / "src" / "trading_bot" / "mql5").glob("*.py")
        if path.is_file()
    ]
    for path in sorted(support_sources):
        entries.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return {"algorithm": "sha256", "files": entries, "file_count": len(entries)}


def _iter_mql5_source_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        path for path in root.rglob("*") if path.is_file() and path.suffix in SOURCE_SUFFIXES
    )


def _find_order_call_matches(source_files: list[Path]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for path in source_files:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8", errors="ignore").splitlines(),
            start=1,
        ):
            if ORDER_CALL_RE.search(line):
                matches.append(
                    {
                        "path": str(path),
                        "line": line_number,
                        "text": _redact_text(line.strip()),
                    }
                )
    return matches


def _copy_docs_snapshot(root: Path, destination: Path) -> None:
    for item in DOC_FILES:
        source = root / item
        if not source.exists():
            continue
        if source.is_file():
            _copy_text_file(source, destination / item.name)
            continue
        for path in source.rglob("*"):
            if path.is_file() and path.suffix in DOC_SUFFIXES and not _is_sensitive_like(path):
                _copy_text_file(path, destination / path.relative_to(root))


def _copy_mql5_snapshot(root: Path, destination: Path) -> None:
    source_root = root / "mql5"
    for path in _iter_mql5_source_files(source_root):
        _copy_text_file(path, destination / path.relative_to(source_root))


def _copy_report_inputs(
    *,
    reports_dir: Path,
    paths: list[str | Path | None],
) -> None:
    for raw_path in paths:
        if raw_path is None:
            continue
        path = Path(raw_path)
        if not path.exists() or _is_sensitive_like(path):
            continue
        if path.is_file():
            _copy_text_file(path, reports_dir / path.name)


def _copy_text_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8", errors="ignore")
    destination.write_text(_redact_text(text), encoding="utf-8")


def _read_json_optional(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.exists() or candidate.is_dir():
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return None
    return _redact_payload(payload if isinstance(payload, dict) else {"payload": payload})


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_redact_payload(payload), indent=2), encoding="utf-8")


def _redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if SENSITIVE_KEY_RE.search(str(key)):
                redacted[str(key)] = "<REDACTED>"
            else:
                redacted[str(key)] = _redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    if isinstance(value, str):
        return _redact_text(value)
    return value


def _redact_text(text: str) -> str:
    return SENSITIVE_ASSIGNMENT_RE.sub(
        lambda match: f"{match.group(1)}=<REDACTED>",
        text,
    )


def _is_sensitive_like(path: Path) -> bool:
    name = path.name.lower()
    return (
        name == ".env"
        or name.startswith(".env.")
        or SENSITIVE_KEY_RE.search(name) is not None
    )


def _path_has_evidence(path: str | Path | None) -> bool:
    if path is None:
        return False
    candidate = Path(path)
    if not candidate.exists():
        return False
    if candidate.is_file():
        return candidate.stat().st_size > 0
    return any(item.is_file() for item in candidate.rglob("*"))


def _render_readme(audit_summary: dict[str, Any]) -> str:
    blockers = "\n".join(f"- {item}" for item in audit_summary["known_blockers"])
    return "\n".join(
        [
            "# Native MQL5 EA Audit Package",
            "",
            f"- Package ID: {audit_summary['package_id']}",
            f"- Created at: {audit_summary['created_at']}",
            "- Package type: native_mql5_ea_audit",
            "- Prop firm: Upcomers",
            "- Native MQL5 EA execution path: true",
            "- Python prop execution allowed: false",
            "- Trading enabled by default: false",
            "",
            "This package is ready for source review, compile review, and manual install review.",
            "It is not approval for Trial trading, Surge 2 Step, Vanguard, Challenge, "
            "Verification, Funded, live money, or profitability claims.",
            "",
            "Trial monitor-only testing may be considered only after before-trial blockers "
            "are resolved or explicitly accepted.",
            "",
            "## Blocked Accounts",
            "",
            "- Trial Risk-Free trading: blocked",
            "- Surge 2 Step trading: blocked; exact rules unverified",
            "- Vanguard trading: blocked; exact rules unverified",
            "",
            "## Known Blockers",
            "",
            blockers,
            "",
        ]
    )
