from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_bot.paper.store import append_jsonl


def emit_alert(*, run_dir: str | Path, event: dict[str, Any], console: bool = False) -> None:
    append_jsonl(Path(run_dir) / "alerts.jsonl", event)
    if console:
        print(f"ALERT {event.get('code')}: {event.get('message')}")

