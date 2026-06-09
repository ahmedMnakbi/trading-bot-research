from __future__ import annotations

from trading_bot.reporting.artifacts import write_report_artifacts


def test_report_artifacts_writer_creates_expected_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    output = write_report_artifacts(
        output_dir=tmp_path / "report",
        config_snapshot={"mode": "paper"},
        artifacts={"paper_summary.json": {"ok": True}, "report.md": "# Report"},
    )

    assert (output / "config_snapshot.yaml").exists()
    assert (output / "paper_summary.json").exists()
    assert (output / "report.md").exists()
