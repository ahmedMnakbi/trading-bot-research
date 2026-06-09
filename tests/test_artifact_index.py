from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from trading_bot.ops.artifact_index import artifact_kind, index_artifacts, sha256_file


def test_artifact_index_computes_sha256_and_kinds(tmp_path: Path) -> None:
    (tmp_path / "data.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
    (tmp_path / "events.jsonl").write_text("{}\n", encoding="utf-8")
    (tmp_path / "report.md").write_text("# Report", encoding="utf-8")
    (tmp_path / "report.html").write_text("<html></html>", encoding="utf-8")
    pd.DataFrame([{"a": 1}]).to_parquet(tmp_path / "rows.parquet", index=False)

    artifacts, warnings = index_artifacts(tmp_path)

    assert not warnings
    assert {item["artifact_kind"] for item in artifacts} >= {
        "json",
        "jsonl",
        "parquet",
        "markdown_report",
        "html_report",
    }
    assert artifacts[0]["sha256"]
    assert sha256_file(tmp_path / "data.json") == next(
        item["sha256"] for item in artifacts if item["relative_path"] == "data.json"
    )
    assert artifact_kind(tmp_path / "config_snapshot.yaml") == "config_snapshot"
