from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from trading_bot.ops.archive import archive_run


def test_archive_run_creates_zip_and_excludes_secrets(tmp_path: Path) -> None:
    run_dir = tmp_path / "reports" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "run_metadata.json").write_text(json.dumps({"run_id": "run1"}), encoding="utf-8")
    (run_dir / "report.md").write_text("# ok", encoding="utf-8")
    (run_dir / ".env").write_text("SECRET=x", encoding="utf-8")

    archive_path, warnings = archive_run("run1", tmp_path)

    assert archive_path.exists()
    assert warnings
    with zipfile.ZipFile(archive_path) as archive:
        assert "report.md" in archive.namelist()
        assert ".env" not in archive.namelist()


def test_archive_run_refuses_paths_outside_processed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    registry = [
        {
            "run_id": "outside",
            "run_type": "report",
            "path": str(outside),
            "created_at": "",
            "artifacts": [],
            "warnings": [],
        }
    ]
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "run_registry.json").write_text(json.dumps(registry), encoding="utf-8")

    with pytest.raises(ValueError):
        archive_run("outside", processed)
