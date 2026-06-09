from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from trading_bot.audit.artifact_scan import scan_artifacts
from trading_bot.audit.code_scan import scan_code
from trading_bot.audit.config_scan import scan_config
from trading_bot.audit.env_scan import scan_environment
from trading_bot.audit.governance import scan_governance
from trading_bot.audit.models import ScanResult, combine_status
from trading_bot.config.settings import Settings
from trading_bot.reporting.artifacts import _json_safe

LIMITATIONS = (
    "Passing this safety audit does not approve live trading. It only confirms that the "
    "repository and local artifacts satisfy the configured safety checks at the time of the "
    "audit. Human approval remains mandatory before any real-money deployment."
)


def run_safety_audit(
    *,
    settings: Settings,
    output_root: str | Path = "data/processed/audits",
    include_code: bool = True,
    include_config: bool = True,
    include_env: bool = True,
    include_artifacts: bool = True,
    project_root: str | Path = ".",
) -> Path:
    audit_run_id = f"audit_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = Path(output_root) / audit_run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    results: dict[str, ScanResult] = {}
    if include_code:
        results["code_scan"] = scan_code(Path(project_root) / "src" / "trading_bot")
    else:
        results["code_scan"] = ScanResult(status="PASS")
    if include_config:
        results["config_scan"] = scan_config(settings)
        results["governance_scan"] = scan_governance(settings.governance)
    else:
        results["config_scan"] = ScanResult(status="PASS")
        results["governance_scan"] = ScanResult(status="PASS")
    if include_env:
        results["env_scan"] = scan_environment(search_root=project_root)
    else:
        results["env_scan"] = ScanResult(status="PASS")
    if include_artifacts:
        results["artifact_scan"] = scan_artifacts(project_root)
    else:
        results["artifact_scan"] = ScanResult(status="PASS")
    audit_result = combine_status(list(results.values()))
    warnings = [warning for result in results.values() for warning in result.warnings]
    failures = [failure for result in results.values() for failure in result.failures]
    metadata = {
        "audit_run_id": audit_run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "audit_result": audit_result,
        "human_approval_required_for_live": settings.governance.require_human_approval_for_live,
    }
    _write_json(output_dir / "audit_summary.json", {"audit_result": audit_result})
    for name, result in results.items():
        _write_json(output_dir / f"{name}.json", asdict(result))
    _write_json(output_dir / "warnings.json", warnings)
    _write_json(output_dir / "failures.json", failures)
    _write_json(output_dir / "run_metadata.json", metadata)
    (output_dir / "report.md").write_text(
        _markdown_report(audit_result, results, warnings, failures),
        encoding="utf-8",
    )
    return output_dir


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(_json_safe(payload), indent=2), encoding="utf-8")


def _markdown_report(
    audit_result: str,
    results: dict[str, ScanResult],
    warnings: list[str],
    failures: list[str],
) -> str:
    return "\n".join(
        [
            "# Safety Audit Report",
            "",
            "## Audit Result",
            audit_result,
            "",
            "## Code Scan",
            str(asdict(results["code_scan"])),
            "",
            "## Config Scan",
            str(asdict(results["config_scan"])),
            "",
            "## Environment Scan",
            str(asdict(results["env_scan"])),
            "",
            "## Artifact Scan",
            str(asdict(results["artifact_scan"])),
            "",
            "## Governance Scan",
            str(asdict(results["governance_scan"])),
            "",
            "## Warnings",
            "\n".join(f"- {warning}" for warning in warnings) if warnings else "- None",
            "",
            "## Failures",
            "\n".join(f"- {failure}" for failure in failures) if failures else "- None",
            "",
            "## Required Actions",
            "Resolve all failures before considering any further review.",
            "",
            "## Important Limitations",
            LIMITATIONS,
        ]
    )

