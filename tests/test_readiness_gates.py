from __future__ import annotations

from trading_bot.reporting.readiness import ReadinessConfig, evaluate_readiness


def config(**overrides):  # type: ignore[no-untyped-def]
    data = {
        "min_paper_runtime_days": 1,
        "min_paper_trades": 1,
        "max_paper_drawdown_pct": 10,
        "max_daily_loss_pct": 1,
        "max_weekly_loss_pct": 3,
        "max_unresolved_alerts": 0,
        "require_no_kill_switch": True,
        "require_no_state_corruption": True,
        "require_validation_reference": True,
        "require_human_approval_for_live": True,
    }
    data.update(overrides)
    return ReadinessConfig(**data)


def metrics(**overrides):  # type: ignore[no-untyped-def]
    data = {
        "runtime_days": 2,
        "number_of_trades": 2,
        "max_drawdown_pct": 1,
        "max_daily_loss_pct": 0,
        "max_weekly_loss_pct": 0,
    }
    data.update(overrides)
    return data


def health(**overrides):  # type: ignore[no-untyped-def]
    data = {"kill_switch_active": False, "state_corruption_detected": False, "unresolved_alerts": 0}
    data.update(overrides)
    return data


def metadata(**overrides):  # type: ignore[no-untyped-def]
    data = {
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
    }
    data.update(overrides)
    return data


def evaluate(**kwargs):  # type: ignore[no-untyped-def]
    return evaluate_readiness(
        metrics=kwargs.get("metrics", metrics()),
        health=kwargs.get("health", health()),
        metadata=kwargs.get("metadata", metadata()),
        validation_run_id=kwargs.get("validation_run_id", "validation-1"),
        config=kwargs.get("config", config()),
    )


def test_readiness_returns_not_ready_when_live_trading_is_true() -> None:
    assert evaluate(metadata=metadata(live_trading=True))["status"] == "NOT_READY"


def test_readiness_returns_not_ready_when_real_orders_are_true() -> None:
    assert evaluate(metadata=metadata(real_orders_enabled=True))["status"] == "NOT_READY"


def test_readiness_returns_not_ready_when_private_api_usage_is_true() -> None:
    assert evaluate(metadata=metadata(uses_private_api=True))["status"] == "NOT_READY"


def test_readiness_returns_not_ready_when_kill_switch_is_active() -> None:
    assert evaluate(health=health(kill_switch_active=True))["status"] == "NOT_READY"


def test_readiness_returns_not_ready_when_drawdown_exceeds_threshold() -> None:
    assert evaluate(metrics=metrics(max_drawdown_pct=11))["status"] == "NOT_READY"


def test_readiness_returns_not_ready_when_unresolved_alerts_exceed_threshold() -> None:
    assert evaluate(health=health(unresolved_alerts=1))["status"] == "NOT_READY"


def test_readiness_returns_not_ready_when_validation_reference_required_but_missing() -> None:
    assert evaluate(validation_run_id=None)["status"] == "NOT_READY"


def test_readiness_returns_needs_more_paper_when_runtime_too_short() -> None:
    assert evaluate(metrics=metrics(runtime_days=0))["status"] == "NEEDS_MORE_PAPER_TRADING"


def test_readiness_returns_needs_more_paper_when_trade_count_too_low() -> None:
    assert evaluate(metrics=metrics(number_of_trades=0))["status"] == "NEEDS_MORE_PAPER_TRADING"


def test_readiness_returns_eligible_for_human_review_only_when_all_gates_pass() -> None:
    assert evaluate()["status"] == "ELIGIBLE_FOR_HUMAN_REVIEW"

