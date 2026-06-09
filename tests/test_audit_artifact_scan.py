from __future__ import annotations

import json

from trading_bot.audit.artifact_scan import scan_artifacts


def write_metadata(tmp_path, key):  # type: ignore[no-untyped-def]
    path = tmp_path / "data" / "processed" / "reports" / "run"
    path.mkdir(parents=True)
    (path / "run_metadata.json").write_text(json.dumps({key: True}), encoding="utf-8")


def test_artifact_scan_fails_if_metadata_has_live_trading_true(tmp_path) -> None:  # type: ignore[no-untyped-def]
    write_metadata(tmp_path, "live_trading")
    assert scan_artifacts(tmp_path).status == "FAIL"


def test_artifact_scan_fails_if_metadata_has_real_orders_enabled_true(tmp_path) -> None:  # type: ignore[no-untyped-def]
    write_metadata(tmp_path, "real_orders_enabled")
    assert scan_artifacts(tmp_path).status == "FAIL"


def test_artifact_scan_fails_if_metadata_has_uses_private_api_true(tmp_path) -> None:  # type: ignore[no-untyped-def]
    write_metadata(tmp_path, "uses_private_api")
    assert scan_artifacts(tmp_path).status == "FAIL"

