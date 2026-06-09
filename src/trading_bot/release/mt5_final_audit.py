from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_bot.audit.reporting import run_safety_audit
from trading_bot.config.settings import load_settings, load_yaml
from trading_bot.reporting.artifacts import _json_safe
from trading_bot.version import __version__


class Mt5FinalAuditPackageError(RuntimeError):
    """Raised when the MT5 Final Audit Agent package cannot be exported."""


MT5_REQUIRED_DOCS = [
    Path("docs/mt5_master_plan.md"),
    Path("docs/upcomers_native_ea_direction_lock.md"),
    Path("docs/mt5_transformation_roadmap.md"),
    Path("docs/mt5_architecture.md"),
    Path("docs/mt5_safety_model.md"),
    Path("docs/mt5_data_ingestion.md"),
    Path("docs/mt5_strategy_research_plan.md"),
    Path("docs/mt5_execution_gates.md"),
    Path("docs/mt5_final_audit_checklist.md"),
    Path("docs/mt5_symbol_mapping.md"),
    Path("docs/feature_matrix.md"),
    Path("docs/known_limitations.md"),
]

MT5_EVIDENCE_ROOTS = {
    "mt5_rates": Path("data/raw/mt5_rates"),
    "mt5_backtests": Path("data/processed/mt5_backtests"),
    "mt5_validations": Path("data/processed/mt5_validations"),
    "mt5_campaigns": Path("data/processed/mt5_campaigns"),
    "mt5_demo_monitor": Path("data/processed/mt5_demo_monitor"),
    "audits": Path("data/processed/audits"),
}

FORBIDDEN_EXECUTION_FEATURES = {
    "live_trading": False,
    "live_account_trading": False,
    "real_orders_enabled": False,
    "python_mt5_execution_enabled": False,
    "uses_private_api": False,
    "balance_fetching_enabled": False,
    "position_fetching_enabled": False,
    "challenge_presets_enabled": False,
}


def export_mt5_final_audit_package(
    *,
    config_path: Path = Path("config/default.yaml"),
    mt5_transformation_config: Path = Path("config/mt5_transformation.yaml"),
    output_root: Path = Path("data/processed/mt5_final_audits"),
    project_root: Path = Path("."),
) -> Path:
    project_root = project_root.resolve()
    _require_files(project_root, [config_path, mt5_transformation_config, *MT5_REQUIRED_DOCS])

    package_id = f"mt5_final_audit_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = output_root / package_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    settings = load_settings(config_path)
    audit_dir = run_safety_audit(settings=settings, project_root=project_root)
    audit_summary = _read_json(audit_dir / "audit_summary.json")
    audit_warnings = _read_json(audit_dir / "warnings.json")
    audit_failures = _read_json(audit_dir / "failures.json")
    audit_metadata = _read_json(audit_dir / "run_metadata.json")

    docs_dir = output_dir / "docs"
    docs_dir.mkdir()
    for doc in MT5_REQUIRED_DOCS:
        _copy_text(project_root / doc, docs_dir / doc.name)

    transformation_snapshot = load_yaml(mt5_transformation_config)
    evidence_index = _build_evidence_index(project_root)
    safety_flags = {
        **FORBIDDEN_EXECUTION_FEATURES,
        "monitor_only_until_native_ea_approval": True,
        "native_mql5_ea_required_for_prop_execution": True,
        "python_mt5_execution_quarantined": True,
        "account_program_awareness_enabled": True,
        "surge_2_step_rule_unverified": True,
        "vanguard_protected_until_exact_rules_and_approval": True,
        "trial_evidence_required_before_challenge": True,
        "prop_day_reset_timezone_requires_verification": True,
        "dynamic_risk_shield_requires_verification": True,
        "human_approval_required_for_live": True,
        "final_audit_agent_review_required": True,
    }
    summary = {
        "package_id": package_id,
        "created_at": datetime.now(UTC).isoformat(),
        "project_version": __version__,
        "status": _package_status(audit_summary, audit_failures),
        "audit_path": str(audit_dir),
        "audit_result": audit_summary.get("audit_result"),
        "warnings": audit_warnings,
        "failures": audit_failures,
        "safety_flags": safety_flags,
        "not_live_approval": True,
        "remaining_required_review": [
            "Final Audit Agent review",
            "Native MQL5 EA source scan PASS and compile PASS",
            "Trial MT5 platform testing evidence",
            "Verified daily loss reset timezone and Dynamic Risk Shield calculation",
            "Human approval before any later live-pilot design",
            "Exact account-program rules before Surge 2 Step, Vanguard, or protected use",
            "Human approval metadata before Challenge, Verification, Funded, Surge 2 Step, "
            "or Vanguard use",
        ],
    }
    metadata = {
        "package_id": package_id,
        "source_release": __version__,
        "created_at": summary["created_at"],
        **safety_flags,
        "audit_run_id": audit_metadata.get("audit_run_id"),
    }

    _write_json(output_dir / "package_summary.json", summary)
    _write_json(output_dir / "run_metadata.json", metadata)
    _write_json(output_dir / "mt5_transformation_config_snapshot.json", transformation_snapshot)
    _write_json(output_dir / "evidence_index.json", evidence_index)
    _write_json(output_dir / "safety_flags.json", safety_flags)
    _copy_text(audit_dir / "report.md", output_dir / "safety_audit_report_snapshot.md")
    _copy_json(audit_dir / "code_scan.json", output_dir / "code_scan_snapshot.json")
    _copy_json(audit_dir / "config_scan.json", output_dir / "config_scan_snapshot.json")
    _copy_json(audit_dir / "env_scan.json", output_dir / "env_scan_snapshot.json")
    _copy_json(audit_dir / "artifact_scan.json", output_dir / "artifact_scan_snapshot.json")
    (output_dir / "final_audit_agent_report.md").write_text(
        _render_report(summary, evidence_index),
        encoding="utf-8",
    )
    return output_dir


def _package_status(audit_summary: dict[str, Any], audit_failures: list[Any]) -> str:
    if audit_failures or audit_summary.get("audit_result") == "FAIL":
        return "FAIL"
    if audit_summary.get("audit_result") == "WARN":
        return "WARN"
    return "READY_FOR_FINAL_AUDIT_REVIEW"


def _build_evidence_index(project_root: Path) -> dict[str, Any]:
    index: dict[str, Any] = {}
    for name, relative_root in MT5_EVIDENCE_ROOTS.items():
        root = project_root / relative_root
        if not root.exists():
            index[name] = {"exists": False, "artifact_count": 0, "latest_artifacts": []}
            continue
        files = sorted(
            [path for path in root.rglob("*") if path.is_file()],
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        index[name] = {
            "exists": True,
            "artifact_count": len(files),
            "latest_artifacts": [str(path.relative_to(project_root)) for path in files[:20]],
        }
    return index


def _render_report(summary: dict[str, Any], evidence_index: dict[str, Any]) -> str:
    evidence_lines = [
        f"- {name}: {details['artifact_count']} artifacts"
        for name, details in evidence_index.items()
    ]
    return "\n".join(
        [
            "# MT5 Final Audit Agent Package",
            "",
            "This package is for Final Audit Agent and human review only.",
            "It is not approval for live trading or real-money deployment.",
            "",
            "## Status",
            str(summary["status"]),
            "",
            "## Safety Flags",
            "- live_trading: false",
            "- live_account_trading: false",
            "- real_orders_enabled: false",
            "- python_mt5_execution_enabled: false",
            "- uses_private_api: false",
            "- balance_fetching_enabled: false",
            "- position_fetching_enabled: false",
            "- monitor_only_until_native_ea_approval: true",
            "- native_mql5_ea_required_for_prop_execution: true",
            "- python_mt5_execution_quarantined: true",
            "- account_program_awareness_enabled: true",
            "- surge_2_step_rule_unverified: true",
            "- vanguard_protected_until_exact_rules_and_approval: true",
            "",
            "## Safety Audit",
            f"- audit_path: {summary['audit_path']}",
            f"- audit_result: {summary['audit_result']}",
            f"- warnings: {summary['warnings']}",
            f"- failures: {summary['failures']}",
            "",
            "## Evidence Index",
            "\n".join(evidence_lines) if evidence_lines else "- No evidence roots found",
            "",
            "## Required Review Before Any Later Live Pilot",
            "- Final Audit Agent review",
            "- Source scan PASS and compile PASS",
            "- Trial MT5 platform testing evidence",
            "- Verified daily loss reset timezone and Dynamic Risk Shield calculation",
            "- Exact account-program rules before Surge 2 Step, Vanguard, or protected use",
            "- Human approval",
            "- Explicit later task approval",
            "",
        ]
    )


def _require_files(project_root: Path, paths: list[Path]) -> None:
    missing = [str(path) for path in paths if not (project_root / path).exists()]
    if missing:
        raise Mt5FinalAuditPackageError(f"missing MT5 final audit inputs: {missing}")


def _copy_text(source: Path, destination: Path) -> None:
    destination.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _copy_json(source: Path, destination: Path) -> None:
    _write_json(destination, _read_json(source))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")
