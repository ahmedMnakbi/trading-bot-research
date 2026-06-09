from __future__ import annotations

import json
from pathlib import Path

from trading_bot.incident.timeline import build_timeline


def write_jsonl(path: Path, payloads: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(payload) for payload in payloads), encoding="utf-8")


def test_incident_timeline_builds_chronological_events(tmp_path: Path) -> None:
    write_jsonl(
        tmp_path / "health_events.jsonl",
        [{"timestamp": "2024-01-01T00:00:02Z", "code": "DATA_STALE", "message": "stale"}],
    )
    write_jsonl(
        tmp_path / "decisions.jsonl",
        [
            {
                "timestamp": "2024-01-01T00:00:01Z",
                "symbol": "BTC/USDT",
                "intent_action": "BUY",
                "portfolio_risk_decision": "accepted",
            }
        ],
    )

    timeline = build_timeline(tmp_path)

    assert [event.event_type for event in timeline] == ["decision", "health"]
    assert timeline[0].symbol == "BTC/USDT"
