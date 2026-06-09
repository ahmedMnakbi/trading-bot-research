from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trading_bot.main import app
from trading_bot.release.mt5_final_audit import (
    Mt5FinalAuditPackageError,
    export_mt5_final_audit_package,
)

ROOT = Path(__file__).resolve().parents[1]


def test_export_mt5_final_audit_package_help_works() -> None:
    result = CliRunner().invoke(app, ["export-mt5-final-audit-package", "--help"])

    assert result.exit_code == 0


def test_mt5_final_audit_package_writes_review_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(ROOT)

    output = export_mt5_final_audit_package(output_root=tmp_path / "final_audits")

    for filename in [
        "package_summary.json",
        "run_metadata.json",
        "mt5_transformation_config_snapshot.json",
        "evidence_index.json",
        "safety_flags.json",
        "safety_audit_report_snapshot.md",
        "code_scan_snapshot.json",
        "config_scan_snapshot.json",
        "env_scan_snapshot.json",
        "artifact_scan_snapshot.json",
        "final_audit_agent_report.md",
    ]:
        assert (output / filename).exists()
    for doc_name in [
        "mt5_master_plan.md",
        "upcomers_native_ea_direction_lock.md",
        "mt5_final_audit_checklist.md",
        "mt5_execution_gates.md",
    ]:
        assert (output / "docs" / doc_name).exists()

    summary = json.loads((output / "package_summary.json").read_text(encoding="utf-8"))
    flags = json.loads((output / "safety_flags.json").read_text(encoding="utf-8"))
    report = (output / "final_audit_agent_report.md").read_text(encoding="utf-8")

    assert summary["not_live_approval"] is True
    assert summary["safety_flags"]["live_trading"] is False
    assert summary["safety_flags"]["real_orders_enabled"] is False
    assert summary["safety_flags"]["python_mt5_execution_enabled"] is False
    assert summary["safety_flags"]["python_mt5_execution_quarantined"] is True
    assert summary["safety_flags"]["native_mql5_ea_required_for_prop_execution"] is True
    assert summary["safety_flags"]["uses_private_api"] is False
    assert summary["safety_flags"]["challenge_presets_enabled"] is False
    assert flags["balance_fetching_enabled"] is False
    assert flags["position_fetching_enabled"] is False
    assert "not approval for live trading" in report
    assert "Source scan PASS and compile PASS" in report


def test_mt5_final_audit_package_requires_inputs(tmp_path: Path) -> None:
    with pytest.raises(Mt5FinalAuditPackageError, match="missing MT5 final audit inputs"):
        export_mt5_final_audit_package(
            config_path=Path("config/default.yaml"),
            mt5_transformation_config=Path("config/mt5_transformation.yaml"),
            output_root=tmp_path / "out",
            project_root=tmp_path,
        )
