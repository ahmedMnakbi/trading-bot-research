from __future__ import annotations

import pytest

from trading_bot.config.settings import ExperimentSettings


def valid_payload() -> dict[str, object]:
    return {
        "enabled": True,
        "output_dir": "data/processed/campaigns",
        "use_cached_data_only": True,
        "write_artifact_manifest": True,
        "symbols": ["BTC/USDT"],
        "timeframes": ["4h"],
        "strategies": ["donchian_breakout"],
        "benchmarks": ["noop", "buy_and_hold"],
        "required_stages": ["backtest", "validation"],
        "review_gates": {
            "min_validation_windows": 1,
            "min_total_test_trades": 0,
            "max_validation_drawdown_pct": 25,
            "max_underperformance_vs_buy_and_hold_pct": 20,
            "require_no_high_severity_warnings": False,
            "require_positive_consistency_score": False,
        },
        "labels": {
            "allow_candidate_labels": True,
            "allowed_labels": ["REJECTED", "NEEDS_MORE_DATA", "PAPER_TRADING_CANDIDATE"],
        },
    }


def test_campaign_config_rejects_unknown_strategy() -> None:
    payload = valid_payload()
    payload["strategies"] = ["unknown"]
    with pytest.raises(ValueError):
        ExperimentSettings.model_validate(payload)


def test_campaign_config_rejects_unknown_benchmark() -> None:
    payload = valid_payload()
    payload["benchmarks"] = ["unknown"]
    with pytest.raises(ValueError):
        ExperimentSettings.model_validate(payload)
