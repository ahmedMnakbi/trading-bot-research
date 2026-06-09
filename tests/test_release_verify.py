from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from trading_bot.main import app
from trading_bot.release.reporting import NON_LIVE_LIMITATION
from trading_bot.release.verify import ReleaseVerificationError, verify_release_candidate


def make_release(tmp_path: Path, metadata: dict[str, object] | None = None) -> Path:
    metadata = metadata or {
        "version": "0.1.0-rc1",
        "release_type": "non_live",
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
    }
    files = {
        "release_manifest.json": "{}",
        "release_summary.json": "{}",
        "release_checklist_snapshot.md": "Live trading is not implemented and is not approved",
        "feature_matrix_snapshot.md": "| Live trading | Not implemented and not approved |",
        "safety_audit_summary.json": "{}",
        "artifact_registry_snapshot.json": "[]",
        "report.md": NON_LIVE_LIMITATION,
        "run_metadata.json": json.dumps(metadata),
    }
    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    return tmp_path


def test_verify_release_candidate_help_works() -> None:
    result = CliRunner().invoke(app, ["verify-release-candidate", "--help"])

    assert result.exit_code == 0


def test_release_verification_passes_for_safe_package(tmp_path: Path) -> None:
    assert verify_release_candidate(make_release(tmp_path))["status"] == "PASS"


@pytest.mark.parametrize("key", ["live_trading", "real_orders_enabled", "uses_private_api"])
def test_release_verification_fails_for_unsafe_metadata(tmp_path: Path, key: str) -> None:
    metadata = {
        "version": "0.1.0-rc1",
        "release_type": "non_live",
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
    }
    metadata[key] = True

    with pytest.raises(ReleaseVerificationError):
        verify_release_candidate(make_release(tmp_path, metadata))


def test_release_verification_fails_for_sensitive_file(tmp_path: Path) -> None:
    release = make_release(tmp_path)
    (release / ".env").write_text("x=y", encoding="utf-8")

    with pytest.raises(ReleaseVerificationError):
        verify_release_candidate(release)
