from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_bot.mql5.models import ComplianceReportArtifacts

DEFAULT_OUTPUT_ROOT = Path("data/processed/prop_compliance_reports")


def export_prop_compliance_report(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_ROOT,
    source_scan_path: str | Path | None = None,
    compile_log_path: str | Path | None = None,
    settings_summary_path: str | Path | None = None,
    log_summary_path: str | Path | None = None,
    trial_evidence_path: str | Path | None = None,
    strategy_tester_evidence_path: str | Path | None = None,
    project_root: str | Path = ".",
) -> ComplianceReportArtifacts:
    root = Path(project_root).resolve()
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    report_id = f"prop_compliance_{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    report_json_path = output_root / f"{report_id}.json"
    report_md_path = output_root / f"{report_id}.md"

    source_scan = _read_json_optional(source_scan_path)
    settings_summary = _read_json_optional(settings_summary_path)
    log_summary = _read_json_optional(log_summary_path)
    trial_evidence = _read_evidence_optional(trial_evidence_path)
    strategy_tester_evidence = _read_evidence_optional(strategy_tester_evidence_path)
    compile_evidence = _read_text_optional(compile_log_path)
    evidence = {
        "source_scan": _evidence_status(source_scan_path, source_scan),
        "compile_log": _text_evidence_status(compile_log_path, compile_evidence),
        "settings_summary": _evidence_status(settings_summary_path, settings_summary),
        "real_ea_monitor_logs": _monitor_evidence_status(log_summary_path, log_summary),
        "trial_evidence": _evidence_status(
            trial_evidence_path,
            trial_evidence,
            label="Trial evidence",
        ),
        "strategy_tester_evidence": _evidence_status(
            strategy_tester_evidence_path,
            strategy_tester_evidence,
            label="Strategy Tester evidence",
        ),
    }
    blockers = [
        "daily reset timezone confirmation",
        "Dynamic Risk Shield exact calculation",
        "Surge 2 Step exact rules review and encoding",
        "Vanguard exact rules review",
        "trial evidence before protected-stage use",
        "final audit package ID",
        "explicit human approval metadata",
    ]
    build_evidence_complete = all(
        evidence[name]["status"] == "PRESENT"
        for name in ("source_scan", "compile_log", "settings_summary")
    )
    monitor_evidence_complete = evidence["real_ea_monitor_logs"]["status"] == "PRESENT"
    trial_evidence_complete = evidence["trial_evidence"]["status"] == "PRESENT"
    strategy_tester_evidence_complete = (
        evidence["strategy_tester_evidence"]["status"] == "PRESENT"
    )
    evidence_complete = all(
        (
            build_evidence_complete,
            monitor_evidence_complete,
            trial_evidence_complete,
            strategy_tester_evidence_complete,
        )
    )
    payload: dict[str, Any] = {
        "report_id": report_id,
        "created_at": datetime.now(UTC).isoformat(),
        "project_root": str(root),
        "status": "WARN" if not evidence_complete else "PASS",
        "evidence_complete": evidence_complete,
        "build_evidence_complete": build_evidence_complete,
        "monitor_evidence_complete": monitor_evidence_complete,
        "trial_evidence_complete": trial_evidence_complete,
        "strategy_tester_evidence_complete": strategy_tester_evidence_complete,
        "evidence": evidence,
        "upcomers_rule_mapping": {
            "daily_loss_limit": {
                "prop_limit": "4%",
                "ea_hard_limit": "3%",
                "status": "stricter_than_prop_cap",
            },
            "overall_loss_limit": {
                "prop_limit": "7%",
                "ea_hard_limit": "6%",
                "status": "stricter_than_prop_cap",
            },
            "minimum_hold_time": {
                "ea_min_hold_seconds": 180,
                "status": "guarded",
            },
            "prohibited_behaviors": {
                "grid": False,
                "martingale": False,
                "averaging_down": False,
                "hft": False,
                "arbitrage": False,
                "copy_trading": False,
                "sub_2_minute_scalping": False,
            },
        },
        "safety_statements": {
            "trading_disabled_by_default": True,
            "python_is_execution_layer": False,
            "python_role": "support-only: scanning, settings, log parsing, reporting",
            "account_program_awareness": [
                "TrialRiskFree",
                "Vanguard",
                "Surge2Step",
                "Custom",
            ],
            "trial_risk_free_first_testing_account": True,
            "surge_2_step_rule_unverified": True,
            "vanguard_blocked": True,
            "protected_account_programs_blocked": True,
            "challenge_funded_blocked_without_approval": True,
            "mql5_order_placement_approved": False,
        },
        "blockers": blockers,
        "source_scan_summary": source_scan,
        "settings_summary": settings_summary,
        "log_summary": log_summary,
        "trial_evidence_path": str(trial_evidence_path) if trial_evidence_path else "",
        "strategy_tester_evidence_path": (
            str(strategy_tester_evidence_path) if strategy_tester_evidence_path else ""
        ),
        "compile_log_path": str(compile_log_path) if compile_log_path else "",
    }
    report_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    report_md_path.write_text(_render_markdown(payload), encoding="utf-8")
    return ComplianceReportArtifacts(
        status=payload["status"],
        report_json_path=str(report_json_path),
        report_md_path=str(report_md_path),
        message="prop-firm compliance report exported",
        evidence_complete=evidence_complete,
        build_evidence_complete=build_evidence_complete,
        monitor_evidence_complete=monitor_evidence_complete,
        trial_evidence_complete=trial_evidence_complete,
        strategy_tester_evidence_complete=strategy_tester_evidence_complete,
        blockers=blockers,
    )


def _read_json_optional(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.exists():
        return None
    try:
        payload = json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else {"payload": payload}


def _read_text_optional(path: str | Path | None) -> str:
    if path is None:
        return ""
    candidate = Path(path)
    if not candidate.exists():
        return ""
    return candidate.read_text(encoding="utf-8", errors="ignore")


def _read_evidence_optional(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    candidate = Path(path)
    if not candidate.exists():
        return None
    if candidate.is_dir():
        files = [item for item in candidate.rglob("*") if item.is_file()]
        return {"path": str(candidate), "file_count": len(files)} if files else None
    json_payload = _read_json_optional(path)
    if json_payload is not None:
        return json_payload
    text = _read_text_optional(path)
    return {"path": str(candidate), "bytes": len(text)} if text else None


def _evidence_status(
    path: str | Path | None,
    payload: dict[str, Any] | None,
    *,
    label: str = "evidence",
) -> dict[str, str]:
    if path is None:
        return {"status": "MISSING", "path": "", "message": f"{label} path not supplied"}
    if payload is None:
        return {"status": "MISSING", "path": str(path), "message": f"{label} unavailable"}
    return {"status": "PRESENT", "path": str(path), "message": f"{label} loaded"}


def _text_evidence_status(path: str | Path | None, text: str) -> dict[str, str]:
    if path is None:
        return {"status": "MISSING", "path": "", "message": "compile log path not supplied"}
    if not text:
        return {"status": "MISSING", "path": str(path), "message": "compile log unavailable"}
    return {"status": "PRESENT", "path": str(path), "message": "compile log loaded"}


def _monitor_evidence_status(
    path: str | Path | None,
    payload: dict[str, Any] | None,
) -> dict[str, str]:
    if path is None:
        return {
            "status": "MISSING",
            "path": "",
            "message": "real EA monitor log summary path not supplied",
        }
    if payload is None:
        return {"status": "MISSING", "path": str(path), "message": "monitor logs unavailable"}
    if payload.get("status") != "PASS" or int(payload.get("files_scanned") or 0) <= 0:
        return {
            "status": "INCOMPLETE",
            "path": str(path),
            "message": "real EA monitor logs missing or skipped",
        }
    return {"status": "PRESENT", "path": str(path), "message": "real EA monitor logs loaded"}


def _render_markdown(payload: dict[str, Any]) -> str:
    evidence_lines = [
        f"- {name}: {details['status']} ({details['message']})"
        for name, details in payload["evidence"].items()
    ]
    blocker_lines = [f"- {blocker}" for blocker in payload["blockers"]]
    return "\n".join(
        [
            "# Prop-Firm Compliance Report",
            "",
            f"- Status: {payload['status']}",
            f"- Evidence complete: {str(payload['evidence_complete']).lower()}",
            f"- Build evidence complete: {str(payload['build_evidence_complete']).lower()}",
            f"- Monitor evidence complete: {str(payload['monitor_evidence_complete']).lower()}",
            f"- Trial evidence complete: {str(payload['trial_evidence_complete']).lower()}",
            "- Strategy Tester evidence complete: "
            f"{str(payload['strategy_tester_evidence_complete']).lower()}",
            "",
            "## Upcomers Rule Mapping",
            "",
            "- Daily loss cap: Upcomers 4%, EA hard guard 3%.",
            "- Overall loss cap: Upcomers 7%, EA hard guard 6%.",
            "- Minimum hold guard: 180 seconds.",
            "- Prohibited behavior flags: no grid, martingale, averaging down, HFT, "
            "arbitrage, copy trading, or sub-2-minute scalping.",
            "",
            "## Safety Boundary",
            "",
            "- Trading disabled by default.",
            "- Python is not the execution layer.",
            "- Python remains support-only for scanning, settings, log parsing, and reporting.",
            "- AccountProgram supports TrialRiskFree, Vanguard, Surge2Step, and Custom.",
            "- Trial Risk-Free remains the first MT5 platform testing environment.",
            "- Surge 2 Step is rule-unverified and blocked until exact rules are reviewed.",
            "- Vanguard remains blocked until exact rules, trial evidence, audit package, "
            "and explicit approval metadata exist.",
            "",
            "## Evidence",
            "",
            "\n".join(evidence_lines),
            "",
            "## Unresolved Blockers",
            "",
            "\n".join(blocker_lines),
            "",
        ]
    )
