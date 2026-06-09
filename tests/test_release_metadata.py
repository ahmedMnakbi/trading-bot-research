from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts import clean_artifacts, generate_fixture_data
from trading_bot.data.cache import cache_file_path, metadata_file_path

ROOT = Path(__file__).resolve().parents[1]


def test_generate_fixture_data_writes_expected_cache_files(tmp_path: Path) -> None:
    written = generate_fixture_data.generate_fixtures(tmp_path)

    assert len(written) == 4
    for symbol in generate_fixture_data.FIXTURE_SYMBOLS:
        for timeframe in generate_fixture_data.FIXTURE_TIMEFRAMES:
            assert cache_file_path(tmp_path, "kraken", symbol, timeframe).exists()


def test_generated_fixture_metadata_includes_fixture_source(tmp_path: Path) -> None:
    generate_fixture_data.generate_fixtures(tmp_path)

    metadata_path = metadata_file_path(tmp_path, "kraken", "BTC/USDT", "4h")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["source"] == "fixture_generated"
    assert metadata["rows"] >= 900


def test_clean_artifacts_dry_run_does_not_delete_files(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(clean_artifacts, "repo_root", lambda: tmp_path)
    artifact = tmp_path / "data/processed/backtests/example/result.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}", encoding="utf-8")

    clean_artifacts.clean_artifacts(dry_run=True)

    assert artifact.exists()


def test_clean_artifacts_deletes_generated_processed_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(clean_artifacts, "repo_root", lambda: tmp_path)
    artifact_dir = tmp_path / "data/processed/reports/example"
    artifact_dir.mkdir(parents=True)

    clean_artifacts.clean_artifacts()

    assert not artifact_dir.exists()


def test_clean_artifacts_deletes_generated_tool_caches(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(clean_artifacts, "repo_root", lambda: tmp_path)
    cache_dir = tmp_path / ".ruff_cache"
    cache_dir.mkdir()

    clean_artifacts.clean_artifacts()

    assert not cache_dir.exists()


def test_clean_artifacts_does_not_delete_raw_data_by_default(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(clean_artifacts, "repo_root", lambda: tmp_path)
    raw_file = tmp_path / "data/raw/ohlcv/kraken/BTC_USDT/4h.parquet"
    raw_file.parent.mkdir(parents=True)
    raw_file.write_text("fixture", encoding="utf-8")

    clean_artifacts.clean_artifacts()

    assert raw_file.exists()


def test_clean_artifacts_include_raw_data_can_delete_raw_fixture_data(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(clean_artifacts, "repo_root", lambda: tmp_path)
    raw_dir = tmp_path / "data/raw/ohlcv"
    raw_dir.mkdir(parents=True)

    clean_artifacts.clean_artifacts(include_raw_data=True)

    assert not raw_dir.exists()


def test_ci_workflow_exists_with_required_jobs() -> None:
    workflow_path = ROOT / ".github/workflows/ci.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    assert set(workflow["jobs"]) >= {"lint", "test", "config-validation", "safety-audit"}


def test_release_checklist_contains_live_trading_prohibition() -> None:
    text = (ROOT / "docs/release_checklist.md").read_text(encoding="utf-8")

    assert (
        "Live trading is not implemented and is not approved. Real orders, authenticated "
        "exchange clients, private account endpoints, leverage, and short selling remain "
        "forbidden."
    ) in text


def test_operator_runbook_contains_safe_command_sequence() -> None:
    text = (ROOT / "docs/operator_runbook.md").read_text(encoding="utf-8")
    expected_commands = [
        "python -m trading_bot validate-config --config config/default.yaml",
        (
            "python -m trading_bot fetch-ohlcv --exchange kraken --symbol BTC/USDT "
            "--timeframe 4h --since-days 365"
        ),
        "python -m trading_bot inspect-data --exchange kraken --symbol BTC/USDT --timeframe 4h",
        (
            "python -m trading_bot run-backtest --config config/default.yaml --exchange "
            "kraken --symbol BTC/USDT --timeframe 4h --strategy donchian_breakout"
        ),
        (
            "python -m trading_bot run-validation --config config/default.yaml --exchange "
            "kraken --symbol BTC/USDT --timeframe 4h"
        ),
        "python -m trading_bot run-campaign --config config/default.yaml --exchange kraken",
        (
            "python -m trading_bot run-paper --config config/default.yaml --exchange "
            "kraken --symbol BTC/USDT --timeframe 4h --strategy donchian_breakout "
            "--validation-run-id <validation_run_id>"
        ),
        (
            "python -m trading_bot report-paper --config config/default.yaml --paper-run-id "
            "<paper_run_id> --validation-run-id <validation_run_id>"
        ),
        "python -m trading_bot run-safety-audit --config config/default.yaml",
    ]

    positions = [text.index(command) for command in expected_commands]
    assert positions == sorted(positions)


def test_operator_runbook_contains_forbidden_work_section() -> None:
    text = (ROOT / "docs/operator_runbook.md").read_text(encoding="utf-8")

    assert "Forbidden Commands / Forbidden Work" in text
    assert "must not run real orders" in text
    assert "private API clients" in text
