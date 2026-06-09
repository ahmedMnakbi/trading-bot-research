from __future__ import annotations

import json

from trading_bot.paper.decision_log import PaperDecisionLogger


def test_decision_log_writes_one_jsonl_record_per_processed_candle(tmp_path) -> None:  # type: ignore[no-untyped-def]
    logger = PaperDecisionLogger(tmp_path)
    logger.write("paper-test", {"live_trading": False, "real_order": False})

    lines = (tmp_path / "paper-test" / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1


def test_decision_log_includes_live_trading_and_real_order_false(tmp_path) -> None:  # type: ignore[no-untyped-def]
    logger = PaperDecisionLogger(tmp_path)
    logger.write("paper-test", {"live_trading": False, "real_order": False})

    payload = json.loads((tmp_path / "paper-test" / "decisions.jsonl").read_text(encoding="utf-8"))
    assert payload["live_trading"] is False
    assert payload["real_order"] is False

