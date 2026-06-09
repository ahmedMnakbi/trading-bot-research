from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def health_event(code: str, message: str, **metadata: Any) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(UTC),
        "code": code,
        "message": message,
        "metadata": metadata,
        "live_trading": False,
    }

