from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml
from typer.testing import CliRunner

from trading_bot.data.models import OhlcvCandle
from trading_bot.main import app


class MockProvider:
    def __init__(self, *_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
        pass

    def fetch_ohlcv(
        self, symbol: str, timeframe: str, since_ms: int, limit: int
    ) -> list[OhlcvCandle]:
        return [
            OhlcvCandle(
                timestamp=datetime(2024, 1, 1, tzinfo=UTC),
                open=100,
                high=110,
                low=90,
                close=105,
                volume=1,
            ),
            OhlcvCandle(
                timestamp=datetime(2024, 1, 1, 4, tzinfo=UTC),
                open=105,
                high=115,
                low=95,
                close=110,
                volume=2,
            ),
        ]


def make_config(tmp_path: Path) -> Path:
    data = yaml.safe_load(Path("config/default.yaml").read_text(encoding="utf-8"))
    data["data"]["cache_dir"] = str(tmp_path / "cache")
    data["data"]["allow_partial_latest_candle"] = True
    data["data"]["validate_continuity"] = True
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_fetch_ohlcv_cli_writes_cache_with_mock_provider(
    tmp_path: Path, monkeypatch
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("trading_bot.main.CcxtOhlcvProvider", MockProvider)
    runner = CliRunner()
    config = make_config(tmp_path)

    result = runner.invoke(
        app,
        [
            "fetch-ohlcv",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
            "--since-days",
            "30",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / "cache" / "kraken" / "BTC_USDT" / "4h.parquet").exists()
    assert (tmp_path / "cache" / "kraken" / "BTC_USDT" / "4h.metadata.json").exists()


def test_inspect_data_reports_quality_metrics(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("trading_bot.main.CcxtOhlcvProvider", MockProvider)
    runner = CliRunner()
    config = make_config(tmp_path)
    fetch_result = runner.invoke(
        app,
        [
            "fetch-ohlcv",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
        ],
    )
    assert fetch_result.exit_code == 0, fetch_result.output

    result = runner.invoke(
        app,
        [
            "inspect-data",
            "--config",
            str(config),
            "--exchange",
            "kraken",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "4h",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "number of candles: 2" in result.output
    assert "missing candle count: 0" in result.output
    assert "duplicate count: 0" in result.output
    assert "invalid OHLCV row count: 0" in result.output
