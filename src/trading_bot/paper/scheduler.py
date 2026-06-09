from __future__ import annotations

from collections.abc import Iterator


def iteration_schedule(max_iterations: int | None) -> Iterator[int]:
    count = max_iterations if max_iterations is not None else 1
    yield from range(count)

