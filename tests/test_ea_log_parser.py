from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import parse_ea_logs
from trading_bot.mql5.log_parser import parse_ea_logs as parse_logs


def test_log_parser_handles_jsonl_logs(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    (log_dir / "ea.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "timestamp": "2026-05-31T16:00:00Z",
                        "strategy": "OpeningRangeBreakout",
                        "signal": "ENTER_LONG_INTENT",
                        "reason_code": "ORB_BREAK_ABOVE_RANGE",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-05-31T16:01:00Z",
                        "strategy": "VWAPTrendContinuation",
                        "signal": "SKIP_SESSION",
                        "reason_code": "SKIP_SESSION",
                    }
                ),
                json.dumps(
                    {
                        "timestamp": "2026-05-31T16:02:00Z",
                        "component": "TradeManager",
                        "message": "REFUSED Phase 6 no-trade TradeManager",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = parse_logs(log_dir, output_dir=tmp_path / "out")

    assert summary.status == "PASS"
    assert summary.decisions_by_strategy["OpeningRangeBreakout"] == 1
    assert summary.entry_intent_count == 1
    assert summary.session_blocks
    assert summary.refused_trade_action_count == 1
    assert Path(summary.summary_json_path).exists()


def test_log_parser_handles_missing_logs_gracefully(tmp_path: Path) -> None:
    summary = parse_logs(tmp_path / "missing", output_dir=tmp_path / "out")

    assert summary.status == "SKIPPED"
    assert summary.files_scanned == 0
    assert Path(summary.summary_json_path).exists()


def test_parse_ea_logs_script_help_works(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        parse_ea_logs.main(["--help"])

    assert excinfo.value.code == 0
    assert "Parse monitor-only" in capsys.readouterr().out
