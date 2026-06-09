from __future__ import annotations

from scripts import operator_smoke


def test_operator_smoke_runs_without_internet() -> None:
    assert operator_smoke.main() == 0
