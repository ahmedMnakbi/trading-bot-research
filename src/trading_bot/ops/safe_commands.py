from __future__ import annotations


def safe_workflow() -> str:
    commands = [
        "python -m trading_bot validate-config --config config/default.yaml",
        "python scripts/generate_fixture_data.py",
        (
            "python -m trading_bot inspect-data --exchange kraken --symbol BTC/USDT "
            "--timeframe 4h"
        ),
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
            "python -m trading_bot run-paper --config config/default.yaml --exchange kraken "
            "--symbol BTC/USDT --timeframe 4h --strategy donchian_breakout "
            "--validation-run-id <validation_run_id>"
        ),
        (
            "python -m trading_bot run-portfolio-paper --config config/default.yaml "
            "--exchange kraken --symbols BTC/USDT,ETH/USDT --timeframe 4h "
            "--max-iterations 3"
        ),
        (
            "python -m trading_bot report-paper --config config/default.yaml "
            "--paper-run-id <paper_run_id> --validation-run-id <validation_run_id>"
        ),
        (
            "python -m trading_bot report-portfolio-paper --config config/default.yaml "
            "--portfolio-paper-run-id <portfolio_paper_run_id>"
        ),
        "python -m trading_bot run-safety-audit --config config/default.yaml",
        "python -m trading_bot index-artifacts",
    ]
    return "\n".join(
        [
            "Safe non-live workflow:",
            *commands,
            "",
            (
                "Live trading is not implemented or approved. Real orders, authenticated "
                "exchange clients, private account endpoints, borrowed exposure, and short selling "
                "remain forbidden."
            ),
        ]
    )
