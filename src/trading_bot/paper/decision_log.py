from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_bot.paper.store import append_jsonl


class PaperDecisionLogger:
    def __init__(self, decision_log_dir: str | Path) -> None:
        self.decision_log_dir = Path(decision_log_dir)

    def write(self, paper_run_id: str, record: dict[str, Any]) -> None:
        append_jsonl(self.decision_log_dir / paper_run_id / "decisions.jsonl", record)

