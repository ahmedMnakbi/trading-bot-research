from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KillSwitchState:
    armed: bool = True
    shutdown: bool = False
    reason: str | None = None


class KillSwitch:
    def __init__(self, *, armed: bool = True) -> None:
        self._state = KillSwitchState(armed=armed)

    @property
    def state(self) -> KillSwitchState:
        return self._state

    def trigger(self, reason: str) -> KillSwitchState:
        if self._state.armed:
            self._state = KillSwitchState(armed=True, shutdown=True, reason=reason)
        return self._state

    def check_drawdown(
        self, *, current_drawdown_pct: float, max_drawdown_pct: float
    ) -> KillSwitchState:
        if current_drawdown_pct >= max_drawdown_pct:
            return self.trigger("max_drawdown_exceeded")
        return self._state

    def check_stale_data(self, *, stale_data: bool) -> KillSwitchState:
        if stale_data:
            return self.trigger("stale_data")
        return self._state

    def check_repeated_order_errors(
        self, *, error_count: int, max_errors: int = 3
    ) -> KillSwitchState:
        if error_count >= max_errors:
            return self.trigger("repeated_order_errors")
        return self._state
