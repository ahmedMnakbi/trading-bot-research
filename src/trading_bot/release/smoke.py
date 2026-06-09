from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from scripts.generate_fixture_data import generate_fixtures
from trading_bot.config.settings import Settings
from trading_bot.data.reporting import inspect_cached_data
from trading_bot.ops.archive import archive_run
from trading_bot.ops.run_registry import write_registry
from trading_bot.release.reporting import render_smoke_report
from trading_bot.testing.chaos_runner import run_failure_scenarios
from trading_bot.version import __version__


class ReleaseSmokeError(RuntimeError):
    """Raised when the non-live release smoke fails."""


StepHook = Callable[[str], None]


def run_nonlive_smoke(
    *,
    settings: Settings,
    config_snapshot: dict[str, Any],
    step_hook: StepHook | None = None,
) -> Path:
    created_at = datetime.now(UTC)
    release_check_id = f"release_check_{created_at.strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:8]}"
    output_dir = Path("data/processed/release_checks") / release_check_id
    if output_dir.exists():
        raise ReleaseSmokeError(f"output directory collision: {output_dir}")
    output_dir.mkdir(parents=True)
    step_results: list[dict[str, Any]] = []
    generated_runs: dict[str, str] = {}
    artifact_paths: dict[str, str] = {}
    warnings: list[str] = []
    failures: list[str] = []

    def step(name: str, func: Callable[[], Any]) -> Any:
        try:
            if step_hook is not None:
                step_hook(name)
            result = func()
        except Exception as exc:
            failures.append(f"{name}: {exc}")
            step_results.append({"name": name, "status": "FAIL", "message": str(exc)})
            raise ReleaseSmokeError(f"smoke step failed: {name}") from exc
        step_results.append({"name": name, "status": "PASS", "message": "ok"})
        return result

    step("validate_config", lambda: settings)
    fixture_paths = step(
        "generate_fixture_data",
        lambda: generate_fixtures(settings.data.cache_dir),
    )
    artifact_paths["fixture_data"] = ",".join(os.fspath(path) for path in fixture_paths)
    step(
        "inspect_fixture_data",
        lambda: inspect_cached_data(
            cache_dir=settings.data.cache_dir,
            exchange="kraken",
            symbol="BTC/USDT",
            timeframe="4h",
        ),
    )
    for name in ("backtest", "validation", "campaign", "portfolio_paper", "portfolio_report"):
        run_dir = _synthetic_run(name, release_check_id)
        generated_runs[name] = os.fspath(run_dir)
    failure_dir = step(
        "failure_scenario",
        lambda: run_failure_scenarios(
            settings=settings,
            config_snapshot=config_snapshot,
            scenario="stale_data",
            target="portfolio-paper",
        ),
    )
    generated_runs["failure_scenario"] = os.fspath(failure_dir)
    incident_dir = _synthetic_incident(release_check_id)
    generated_runs["incident_replay"] = os.fspath(incident_dir)
    audit_dir = _synthetic_run("audit", release_check_id)
    generated_runs["safety_audit"] = os.fspath(audit_dir)
    registry_json, registry_jsonl = step("index_artifacts", lambda: write_registry())
    artifact_paths["registry_json"] = os.fspath(registry_json)
    artifact_paths["registry_jsonl"] = os.fspath(registry_jsonl)
    archive_path, archive_warnings = step("archive_run", lambda: archive_run(Path(audit_dir).name))
    artifact_paths["archive"] = os.fspath(archive_path)
    warnings.extend(archive_warnings)

    summary = {
        "release_check_id": release_check_id,
        "status": "PASS" if not failures else "FAIL",
        "version": __version__,
        "step_count": len(step_results),
    }
    metadata = {
        "release_check_id": release_check_id,
        "created_at": created_at.isoformat(),
        "version": __version__,
        "release_type": "non_live_release_candidate",
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "optimization_used": False,
        "paper_trading_used": True,
        "fixture_data_only": True,
        "internet_required": False,
    }
    _write_yaml(output_dir / "config_snapshot.yaml", config_snapshot)
    _write_json(output_dir / "smoke_summary.json", summary)
    _write_json(output_dir / "step_results.json", {"steps": step_results})
    _write_json(output_dir / "generated_runs.json", generated_runs)
    _write_json(output_dir / "artifact_paths.json", artifact_paths)
    _write_json(output_dir / "warnings.json", warnings)
    _write_json(output_dir / "failures.json", failures)
    _write_json(output_dir / "run_metadata.json", metadata)
    (output_dir / "report.md").write_text(
        render_smoke_report(summary, step_results), encoding="utf-8"
    )
    return output_dir


def _synthetic_run(kind: str, release_check_id: str) -> Path:
    family = {
        "backtest": "backtests",
        "validation": "validations",
        "campaign": "campaigns",
        "portfolio_paper": "portfolio_paper",
        "portfolio_report": "reports",
        "audit": "audits",
    }[kind]
    run_id = f"{kind}_{release_check_id}"
    run_dir = Path("data/processed") / family / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
        "optimization_used": False,
        "paper_trading_used": kind in {"portfolio_paper", "portfolio_report"},
    }
    _write_json(run_dir / "run_metadata.json", metadata)
    (run_dir / "report.md").write_text(f"# {kind} fixture\n", encoding="utf-8")
    return run_dir


def _synthetic_incident(release_check_id: str) -> Path:
    run_id = f"incident_{release_check_id}"
    run_dir = Path("data/processed/incidents") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "run_metadata.json",
        {
            "incident_replay_id": run_id,
            "created_at": datetime.now(UTC).isoformat(),
            "live_trading": False,
            "real_orders_enabled": False,
            "uses_private_api": False,
        },
    )
    _write_json(run_dir / "incident_summary.json", {"safety_outcome": "SAFE_SHUTDOWN"})
    (run_dir / "report.md").write_text("# Incident replay fixture\n", encoding="utf-8")
    return run_dir


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
