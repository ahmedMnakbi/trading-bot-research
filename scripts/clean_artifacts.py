from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROCESSED_TARGETS = (
    Path("data/processed"),
    Path("data/processed/backtests"),
    Path("data/processed/validations"),
    Path("data/processed/paper"),
    Path("data/processed/reports"),
    Path("data/processed/audits"),
    Path("data/processed/campaigns"),
    Path("data/processed/portfolio_paper"),
    Path("data/processed/failure_tests"),
    Path("data/processed/incidents"),
    Path("data/processed/archives"),
    Path("data/processed/run_registry.json"),
    Path("data/processed/run_registry.jsonl"),
    Path("data/processed/release_checks"),
    Path("data/processed/releases"),
    Path("data/processed/human_review"),
    Path("data/processed/ea_log_summaries"),
    Path("data/processed/ea_settings"),
    Path("data/processed/mql5_compile"),
    Path("data/processed/mql5_source_scan"),
    Path("data/processed/mt5_demo_monitor"),
    Path("data/processed/mt5_final_audits"),
    Path("data/processed/prop_compliance_reports"),
    Path("data/processed/robustness"),
)
RAW_TARGETS = (Path("data/raw/ohlcv"),)
CACHE_TARGETS = (
    Path(".pytest_cache"),
    Path(".ruff_cache"),
    Path("tmp"),
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_inside_project(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(root)
    return resolved


def known_targets(include_raw_data: bool) -> list[Path]:
    root = repo_root()
    targets = [root / target for target in (*CACHE_TARGETS, *PROCESSED_TARGETS)]
    targets.extend(path for path in root.rglob("__pycache__") if path.is_dir())
    if include_raw_data:
        targets.extend(root / target for target in RAW_TARGETS)
    return targets


def clean_artifacts(*, dry_run: bool = False, include_raw_data: bool = False) -> list[Path]:
    root = repo_root().resolve()
    removed: list[Path] = []
    for target in known_targets(include_raw_data):
        resolved = ensure_inside_project(target, root)
        if not resolved.exists():
            continue
        print(f"{'would remove' if dry_run else 'removing'}: {resolved}")
        if not dry_run:
            try:
                if resolved.is_dir():
                    shutil.rmtree(resolved)
                else:
                    resolved.unlink()
            except OSError as exc:
                print(f"failed to remove {resolved}: {exc}")
                continue
        removed.append(resolved)
    if not removed:
        print("nothing to remove")
    return removed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove generated local artifacts safely.")
    parser.add_argument("--dry-run", action="store_true", help="Print removals without deleting.")
    parser.add_argument(
        "--include-raw-data",
        action="store_true",
        help="Also remove data/raw/ohlcv. This is never done by default.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    clean_artifacts(dry_run=args.dry_run, include_raw_data=args.include_raw_data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
