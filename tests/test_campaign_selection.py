from __future__ import annotations

from types import SimpleNamespace

from trading_bot.experiments.selection import label_candidate


def gates(**overrides):  # type: ignore[no-untyped-def]
    data = {
        "min_validation_windows": 3,
        "min_total_test_trades": 10,
        "max_validation_drawdown_pct": 25,
        "max_underperformance_vs_buy_and_hold_pct": 20,
        "require_no_high_severity_warnings": True,
        "require_positive_consistency_score": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def metrics(**overrides):  # type: ignore[no-untyped-def]
    data = {
        "number_of_failed_stages": 0,
        "validation_total_test_trades": 12,
        "validation_worst_test_drawdown_pct": 5,
        "validation_warning_flags": [],
        "validation_number_of_windows": 3,
        "excess_return_vs_buy_and_hold_pct": 0,
        "validation_consistency_score": 0,
    }
    data.update(overrides)
    return data


def test_candidate_label_rejected_when_validation_fails() -> None:
    assert label_candidate(metrics(number_of_failed_stages=1), gates())[0] == "REJECTED"


def test_candidate_label_rejected_when_zero_trades() -> None:
    assert label_candidate(metrics(validation_total_test_trades=0), gates())[0] == "REJECTED"


def test_candidate_label_rejected_when_drawdown_exceeds_limit() -> None:
    assert label_candidate(metrics(validation_worst_test_drawdown_pct=30), gates())[0] == "REJECTED"


def test_candidate_label_needs_more_data_when_too_few_trades() -> None:
    assert label_candidate(metrics(validation_total_test_trades=5), gates())[0] == "NEEDS_MORE_DATA"


def test_candidate_label_needs_more_data_when_too_few_windows() -> None:
    assert label_candidate(metrics(validation_number_of_windows=1), gates())[0] == "NEEDS_MORE_DATA"


def test_candidate_label_paper_candidate_only_when_all_gates_pass() -> None:
    assert label_candidate(metrics(), gates())[0] == "PAPER_TRADING_CANDIDATE"

