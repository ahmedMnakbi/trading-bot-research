from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

COMMON_METAEDITOR_PATHS = (
    Path("C:/Program Files/MetaTrader 5/metaeditor64.exe"),
    Path("C:/Program Files/MetaTrader 5/metaeditor.exe"),
    Path("C:/Program Files (x86)/MetaTrader 5/metaeditor.exe"),
)
COMMON_TERMINAL_PATHS = (
    Path("C:/Program Files/MetaTrader 5/terminal64.exe"),
    Path("C:/Program Files/MetaTrader 5/terminal.exe"),
    Path("C:/Program Files (x86)/MetaTrader 5/terminal.exe"),
)


@dataclass(frozen=True)
class MetaEditorDetection:
    status: str
    metaeditor_path: str | None
    terminal_path: str | None
    message: str


def first_existing(paths: Sequence[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def detect_metaeditor(
    metaeditor_path: str | Path | None = None,
    terminal_path: str | Path | None = None,
) -> MetaEditorDetection:
    selected_metaeditor = (
        Path(metaeditor_path) if metaeditor_path else first_existing(COMMON_METAEDITOR_PATHS)
    )
    selected_terminal = (
        Path(terminal_path) if terminal_path else first_existing(COMMON_TERMINAL_PATHS)
    )
    metaeditor_ok = selected_metaeditor is not None and selected_metaeditor.exists()
    terminal_ok = selected_terminal is not None and selected_terminal.exists()
    if metaeditor_ok and terminal_ok:
        return MetaEditorDetection(
            "PASS",
            str(selected_metaeditor),
            str(selected_terminal),
            "MetaEditor and MT5 terminal detected; no login attempted",
        )
    if metaeditor_ok:
        return MetaEditorDetection(
            "WARN",
            str(selected_metaeditor),
            None,
            "MetaEditor detected but MT5 terminal was not found; install MT5 manually if needed",
        )
    return MetaEditorDetection(
        "SKIPPED",
        None,
        str(selected_terminal) if terminal_ok else None,
        "MetaEditor not found; install MetaTrader 5 manually or pass --metaeditor-path",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Detect MetaEditor and MT5 terminal paths.")
    parser.add_argument("--metaeditor-path", help="Optional explicit MetaEditor executable path.")
    parser.add_argument("--terminal-path", help="Optional explicit MT5 terminal executable path.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    detection = detect_metaeditor(args.metaeditor_path, args.terminal_path)
    if args.json:
        print(json.dumps(asdict(detection), indent=2))
    else:
        print(f"metaeditor_detection: {detection.status}")
        print(f"metaeditor_path: {detection.metaeditor_path or 'not_found'}")
        print(f"terminal_path: {detection.terminal_path or 'not_found'}")
        print(detection.message)
        print("No MT5 login, credentials, terminal settings, or trading permissions were used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
