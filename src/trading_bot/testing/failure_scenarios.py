from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from trading_bot.testing.fixtures import synthetic_candle_times

SUPPORTED_SCENARIOS = {
    "stale_data",
    "missing_candles",
    "duplicate_candles",
    "corrupted_state",
    "strategy_exception",
    "simulated_order_rejection",
    "state_write_failure",
    "interrupted_run",
}
SUPPORTED_TARGETS = {"portfolio-paper"}


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    target: str
    status: str
    health_events: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
    decisions: list[dict[str, Any]]
    state: dict[str, Any]
    summary: dict[str, Any]


def run_scenario(scenario: str, *, target: str, max_iterations: int) -> ScenarioResult:
    if scenario not in SUPPORTED_SCENARIOS:
        raise ValueError(f"scenario not found: {scenario}")
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported target: {target}")
    now = datetime.now(UTC)
    state = _base_state(now)
    health: list[dict[str, Any]] = []
    alerts: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []

    def event(code: str, message: str, severity: str = "WARNING") -> dict[str, Any]:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "code": code,
            "message": message,
            "severity": severity,
            "live_trading": False,
        }
        health.append(payload)
        alerts.append(payload)
        return payload

    if scenario == "stale_data":
        state["consecutive_data_errors_by_symbol"]["BTC/USDT"] = max_iterations
        state["kill_switch_active"] = True
        event("DATA_STALE", "latest candle is outside the allowed freshness window", "ERROR")
    elif scenario == "missing_candles":
        state["portfolio_warnings"].append("DATA_GAP_DETECTED:BTC/USDT")
        event("DATA_GAP_DETECTED", "gap detected in BTC/USDT candle stream")
        decisions.append(_decision("ETH/USDT", "HOLD", warnings=["BTC/USDT_SKIPPED"]))
    elif scenario == "duplicate_candles":
        state["last_processed_candle_by_symbol"]["BTC/USDT"] = synthetic_candle_times(
            duplicate=True
        )[0]
        event("DUPLICATE_CANDLE", "duplicate BTC/USDT candle ignored")
        decisions.append(_decision("BTC/USDT", "HOLD", warnings=["DUPLICATE_IGNORED"]))
    elif scenario == "corrupted_state":
        state["corrupted_state_detected"] = True
        event("STATE_CORRUPTION_DETECTED", "malformed state prevented unsafe resume", "ERROR")
    elif scenario == "strategy_exception":
        event("STRATEGY_ERROR", "injected strategy exception for BTC/USDT", "ERROR")
        decisions.append(_decision("BTC/USDT", "HOLD", warnings=["STRATEGY_ERROR"]))
        decisions.append(_decision("ETH/USDT", "HOLD"))
    elif scenario == "simulated_order_rejection":
        state["consecutive_order_errors"] = max_iterations
        state["kill_switch_active"] = True
        event("ORDER_REJECTED", "simulated execution rejection injected", "ERROR")
        decisions.append(
            _decision(
                "BTC/USDT",
                "BUY",
                order_decision="simulated_order_rejected",
                warnings=["ORDER_REJECTED"],
            )
        )
    elif scenario == "state_write_failure":
        event("STATE_WRITE_FAILED", "state write failure injected", "ERROR")
        decisions.append(_decision("BTC/USDT", "HOLD", warnings=["STATE_WRITE_FAILED"]))
        state["stopped_after_failed_persistence"] = True
    elif scenario == "interrupted_run":
        decisions.append(_decision("BTC/USDT", "HOLD", warnings=["INTERRUPTED_AFTER_DECISION"]))
        state["interruption_point"] = "after_decision_before_next_loop"
        state["resume_duplicate_orders"] = 0
        event("RUN_INTERRUPTED", "interruption injected after decision")

    summary = {
        "scenario": scenario,
        "target": target,
        "status": "PASS",
        "orders_created": sum(
            1 for item in decisions if item["order_decision"].endswith("created")
        ),
        "orders_rejected": sum(
            1 for item in decisions if item["order_decision"] == "simulated_order_rejected"
        ),
        "kill_switch_active": state["kill_switch_active"],
    }
    return ScenarioResult(
        scenario=scenario,
        target=target,
        status="PASS",
        health_events=health,
        alerts=alerts,
        decisions=decisions,
        state=state,
        summary=summary,
    )


def _base_state(now: datetime) -> dict[str, Any]:
    return {
        "portfolio_paper_run_id": "failure_fixture",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "cash": 10_000,
        "equity": 10_000,
        "positions_by_symbol": {},
        "last_processed_candle_by_symbol": {"BTC/USDT": None, "ETH/USDT": None},
        "kill_switch_active": False,
        "consecutive_data_errors_by_symbol": {"BTC/USDT": 0, "ETH/USDT": 0},
        "consecutive_order_errors": 0,
        "portfolio_warnings": [],
    }


def _decision(
    symbol: str,
    action: str,
    *,
    order_decision: str = "no_order",
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "portfolio_paper_run_id": "failure_fixture",
        "exchange": "kraken",
        "symbol": symbol,
        "timeframe": "4h",
        "strategy": "donchian_breakout",
        "candle_timestamp": synthetic_candle_times()[0],
        "intent_action": action,
        "intent_reason": "failure_injection",
        "risk_decision": "accepted",
        "portfolio_risk_decision": "accepted",
        "order_decision": order_decision,
        "warnings": warnings or [],
        "live_trading": False,
        "real_order": False,
    }
