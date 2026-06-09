from __future__ import annotations

import json
from pathlib import Path

import yaml

from trading_bot.config.settings import Settings
from trading_bot.incident.replay import classify_outcome, replay_run
from trading_bot.incident.reporting import LIMITATIONS, write_incident_replay
from trading_bot.incident.timeline import build_timeline

ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def write_jsonl(path: Path, payloads: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(payload) for payload in payloads), encoding="utf-8")


def make_run(tmp_path: Path, *, kill: bool = False) -> Path:
    tmp_path.mkdir(parents=True)
    write_json(tmp_path / "state.json", {"kill_switch_active": kill, "positions_by_symbol": {}})
    write_json(tmp_path / "run_metadata.json", {"live_trading": False})
    health = []
    if kill:
        health.append(
            {
                "timestamp": "2024-01-01T00:00:01Z",
                "code": "KILL_SWITCH_ACTIVE",
                "message": "KILL_SWITCH_ACTIVE",
                "severity": "ERROR",
            }
        )
    write_jsonl(tmp_path / "health_events.jsonl", health)
    write_jsonl(tmp_path / "alerts.jsonl", health)
    write_jsonl(
        tmp_path / "decisions.jsonl",
        [{"timestamp": "2024-01-01T00:00:00Z", "intent_action": "HOLD"}],
    )
    return tmp_path


def settings_for(tmp_path: Path) -> Settings:
    data = yaml.safe_load((ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    data["incident_replay"]["output_dir"] = str(tmp_path / "incidents")
    return Settings.model_validate(data)


def test_incident_replay_classifies_safe_shutdown(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path / "run", kill=True)

    assert replay_run(run_dir)["outcome"] == "SAFE_SHUTDOWN"


def test_incident_replay_classifies_safe_continuation(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path / "run", kill=False)

    assert replay_run(run_dir)["outcome"] == "SAFE_CONTINUATION"


def test_incident_replay_classifies_unsafe_state() -> None:
    outcome = classify_outcome(
        state={"corrupted_state_detected": True},
        metadata={"live_trading": False},
        timeline=[],
    )

    assert outcome == "UNSAFE_STATE_DETECTED"


def test_incident_replay_classifies_insufficient_artifacts() -> None:
    assert classify_outcome(state={}, metadata={}, timeline=[]) == "INSUFFICIENT_ARTIFACTS"


def test_incident_replay_writes_required_artifacts(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path / "run", kill=True)
    output = write_incident_replay(settings=settings_for(tmp_path), run_dir=run_dir)

    for filename in [
        "incident_summary.json",
        "timeline.json",
        "health_summary.json",
        "alert_summary.json",
        "decision_summary.json",
        "state_summary.json",
        "report.md",
        "run_metadata.json",
    ]:
        assert (output / filename).exists()
    assert LIMITATIONS in (output / "report.md").read_text(encoding="utf-8")


def test_incident_replay_does_not_call_exchanges(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path / "run", kill=False)

    assert build_timeline(run_dir)
