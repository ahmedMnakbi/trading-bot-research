from __future__ import annotations

import json
from pathlib import Path

from trading_bot.ops.run_registry import RUN_FAMILIES, build_run_registry, find_run, write_registry


def make_run(processed: Path, family: str, run_id: str, metadata: dict[str, object] | None) -> Path:
    run_dir = processed / family / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "report.md").write_text("# report", encoding="utf-8")
    if metadata is not None:
        (run_dir / "run_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return run_dir


def test_run_registry_indexes_all_supported_run_types(tmp_path: Path) -> None:
    for family in RUN_FAMILIES:
        make_run(tmp_path, family, f"{family}_run", {"run_id": f"{family}_run"})

    entries = build_run_registry(tmp_path)

    assert {entry["run_type"] for entry in entries} >= set(RUN_FAMILIES.values())


def test_run_registry_handles_missing_and_unsafe_metadata(tmp_path: Path) -> None:
    make_run(tmp_path, "campaigns", "missing", None)
    make_run(tmp_path, "audits", "unsafe", {"run_id": "unsafe", "live_trading": True})

    entries = build_run_registry(tmp_path)

    assert any("metadata missing" in entry["warnings"] for entry in entries)
    assert any("unsafe metadata: live_trading=true" in entry["warnings"] for entry in entries)


def test_registry_write_and_find_run(tmp_path: Path) -> None:
    make_run(tmp_path, "reports", "report_1", {"run_id": "report_1"})
    write_registry(tmp_path)

    assert find_run("report_1", tmp_path) is not None
