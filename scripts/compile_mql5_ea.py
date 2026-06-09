from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.check_metaeditor import detect_metaeditor

EA_RELATIVE_PATH = Path("mql5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5")
COMPILE_LOG_ROOT = Path("data/processed/mql5_compile")


@dataclass(frozen=True)
class CompileResult:
    status: str
    source_path: str
    log_path: str
    message: str
    returncode: int | None = None


def new_log_path(project_root: Path) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = project_root / COMPILE_LOG_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"compile_{timestamp}.log"


def write_log(path: Path, lines: Sequence[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compile_ea(
    project_root: str | Path = ".",
    *,
    metaeditor_path: str | Path | None = None,
) -> CompileResult:
    root = Path(project_root).resolve()
    source = root / EA_RELATIVE_PATH
    log_path = new_log_path(root)
    if not source.exists():
        message = "EA source does not exist yet; compile skipped before Phase 4"
        write_log(log_path, [message, f"expected_source: {source}"])
        return CompileResult("SKIPPED", str(source), str(log_path), message)
    detection = detect_metaeditor(metaeditor_path=metaeditor_path)
    if detection.metaeditor_path is None:
        message = (
            "MetaEditor not found; compile skipped. Install MT5 manually or pass "
            "--metaeditor-path."
        )
        write_log(log_path, [message, f"source: {source}"])
        return CompileResult("SKIPPED", str(source), str(log_path), message)
    command = [
        detection.metaeditor_path,
        f"/compile:{source}",
        f"/log:{log_path}",
    ]
    result = subprocess.run(command, check=False, cwd=root)
    status = "PASS" if result.returncode == 0 else "FAIL"
    if not log_path.exists():
        write_log(log_path, [f"MetaEditor returned {result.returncode}", f"command: {command}"])
    return CompileResult(
        status,
        str(source),
        str(log_path),
        "MetaEditor compile completed" if status == "PASS" else "MetaEditor compile failed",
        result.returncode,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile the future repo-owned MQL5 EA if present."
    )
    parser.add_argument("--project-root", default=".", help="Repository root.")
    parser.add_argument("--metaeditor-path", help="Optional explicit MetaEditor executable path.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = compile_ea(args.project_root, metaeditor_path=args.metaeditor_path)
    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(f"mql5_compile: {result.status}")
        print(f"source_path: {result.source_path}")
        print(f"log_path: {result.log_path}")
        print(result.message)
        print("No MT5 login, prop credentials, or live trading permissions were used.")
    return 1 if result.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
