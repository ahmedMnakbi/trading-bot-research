from __future__ import annotations

from trading_bot.config.settings import load_settings
from trading_bot.testing.failure_scenarios import run_scenario


def test_failure_injection_defaults_disabled() -> None:
    settings = load_settings("config/default.yaml")

    assert settings.failure_injection.enabled is False


def test_stale_data_scenario_emits_data_stale_and_prevents_order() -> None:
    result = run_scenario("stale_data", target="portfolio-paper", max_iterations=5)

    assert any(event["code"] == "DATA_STALE" for event in result.health_events)
    assert result.state["kill_switch_active"] is True
    assert result.summary["orders_created"] == 0


def test_missing_candles_scenario_emits_gap_and_continues() -> None:
    result = run_scenario("missing_candles", target="portfolio-paper", max_iterations=5)

    assert any(event["code"] == "DATA_GAP_DETECTED" for event in result.health_events)
    assert any(decision["symbol"] == "ETH/USDT" for decision in result.decisions)


def test_duplicate_candles_avoid_duplicate_decisions() -> None:
    result = run_scenario("duplicate_candles", target="portfolio-paper", max_iterations=5)

    assert any(event["code"] == "DUPLICATE_CANDLE" for event in result.health_events)
    assert len(result.decisions) == 1
    assert result.summary["orders_created"] == 0


def test_corrupted_state_refuses_unsafe_resume() -> None:
    result = run_scenario("corrupted_state", target="portfolio-paper", max_iterations=5)

    assert result.state["corrupted_state_detected"] is True
    assert any(event["code"] == "STATE_CORRUPTION_DETECTED" for event in result.health_events)
    assert result.summary["orders_created"] == 0


def test_strategy_exception_skips_affected_symbol() -> None:
    result = run_scenario("strategy_exception", target="portfolio-paper", max_iterations=5)

    assert any(event["code"] == "STRATEGY_ERROR" for event in result.health_events)
    btc = [decision for decision in result.decisions if decision["symbol"] == "BTC/USDT"]
    assert btc[0]["order_decision"] == "no_order"


def test_simulated_order_rejection_records_rejection_and_kill_switch() -> None:
    result = run_scenario("simulated_order_rejection", target="portfolio-paper", max_iterations=5)

    assert any(event["code"] == "ORDER_REJECTED" for event in result.health_events)
    assert result.state["consecutive_order_errors"] == 5
    assert result.state["kill_switch_active"] is True
    assert result.summary["orders_rejected"] == 1


def test_state_write_failure_stops_processing() -> None:
    result = run_scenario("state_write_failure", target="portfolio-paper", max_iterations=5)

    assert any(event["code"] == "STATE_WRITE_FAILED" for event in result.health_events)
    assert result.state["stopped_after_failed_persistence"] is True
    assert len(result.decisions) == 1


def test_interrupted_run_resumes_without_duplicate_orders() -> None:
    result = run_scenario("interrupted_run", target="portfolio-paper", max_iterations=5)

    assert result.state["resume_duplicate_orders"] == 0
    assert result.summary["orders_created"] == 0
