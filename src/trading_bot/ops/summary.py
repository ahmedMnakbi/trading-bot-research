from __future__ import annotations

import json
from typing import Any


def format_run(entry: dict[str, Any]) -> str:
    return json.dumps(entry, indent=2)
