from __future__ import annotations

from dataclasses import asdict

from trading_bot.experiments.models import Experiment


def build_experiment_matrix(
    *,
    exchange: str,
    symbols: list[str],
    timeframes: list[str],
    strategies: list[str],
    stages: list[str],
) -> list[Experiment]:
    rows: list[Experiment] = []
    for symbol in symbols:
        for timeframe in timeframes:
            for strategy in strategies:
                experiment_id = f"{exchange}_{symbol.replace('/', '_')}_{timeframe}_{strategy}"
                rows.append(
                    Experiment(
                        experiment_id=experiment_id,
                        exchange=exchange,
                        symbol=symbol,
                        timeframe=timeframe,
                        strategy=strategy,
                        stages=stages,
                    )
                )
    return rows


def matrix_as_dicts(matrix: list[Experiment]) -> list[dict[str, object]]:
    return [asdict(row) for row in matrix]
