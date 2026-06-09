from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from trading_bot.config.settings import load_settings, load_yaml
from trading_bot.main import app
from trading_bot.release.final_check import run_final_nonlive_check
from trading_bot.release.package import build_release_candidate

ROOT = Path(__file__).resolve().parents[1]


def test_final_nonlive_check_help_works() -> None:
    assert CliRunner().invoke(app, ["final-nonlive-check", "--help"]).exit_code == 0


def test_final_nonlive_check_passes_on_safe_fixture_release(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    release_dir = build_release_candidate(
        settings=load_settings("config/default.yaml"),
        config_snapshot=load_yaml(ROOT / "config/default.yaml"),
    )

    result = run_final_nonlive_check(ROOT / "config/default.yaml", release_dir)

    assert result["status"] == "PASS"


def test_final_nonlive_check_fails_when_live_trading_enabled(tmp_path: Path) -> None:
    data = load_yaml(ROOT / "config/default.yaml")
    data["live_trading_enabled"] = True
    config = tmp_path / "config.yaml"
    config.write_text(yaml.safe_dump(data), encoding="utf-8")

    result = run_final_nonlive_check(config, Path("data/processed/releases/0.1.0-rc1"))

    assert result["status"] == "FAIL"


def test_final_nonlive_check_fails_when_release_metadata_has_real_orders(
    tmp_path: Path,
) -> None:
    release_dir = tmp_path / "release"
    release_dir.mkdir()
    for filename in [
        "release_manifest.json",
        "release_summary.json",
        "safety_audit_summary.json",
        "artifact_registry_snapshot.json",
    ]:
        (release_dir / filename).write_text("{}", encoding="utf-8")
    (release_dir / "release_checklist_snapshot.md").write_text(
        "Live trading is not implemented and is not approved", encoding="utf-8"
    )
    (release_dir / "feature_matrix_snapshot.md").write_text(
        "Not implemented and not approved", encoding="utf-8"
    )
    (release_dir / "report.md").write_text(
        "This is a non-live research, backtesting, validation, campaign, and paper-trading "
        "release candidate. It is not approved for real-money trading. Live trading, real order "
        "placement, authenticated exchange clients, private account endpoints, leverage is "
        "forbidden, shorting, optimization, and machine learning remain forbidden.",
        encoding="utf-8",
    )
    (release_dir / "run_metadata.json").write_text(
        json.dumps(
            {
                "version": "0.1.0-rc1",
                "release_type": "non_live",
                "live_trading": False,
                "real_orders_enabled": True,
                "uses_private_api": False,
            }
        ),
        encoding="utf-8",
    )

    result = run_final_nonlive_check(ROOT / "config/default.yaml", release_dir)

    assert result["status"] == "FAIL"
