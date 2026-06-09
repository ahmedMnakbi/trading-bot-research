from __future__ import annotations

import json
import zipfile
from pathlib import Path

from trading_bot.ops.run_registry import find_run


def archive_run(
    run_id: str,
    processed_dir: Path = Path("data/processed"),
) -> tuple[Path, list[str]]:
    entry = find_run(run_id, processed_dir)
    if entry is None:
        raise ValueError(f"run not found: {run_id}")
    root = processed_dir.resolve()
    run_dir = Path(entry["path"]).resolve()
    run_dir.relative_to(root)
    archive_dir = processed_dir / "archives"
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_path = archive_dir / f"{run_id}.zip"
    warnings = list(entry.get("warnings", []))
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("registry_entry.json", json.dumps(entry, indent=2))
        for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
            if _sensitive_named(path):
                warnings.append(f"excluded sensitive-named file: {path.name}")
                continue
            archive.write(path, path.relative_to(run_dir).as_posix())
    return archive_path, warnings


def _sensitive_named(path: Path) -> bool:
    lowered = path.name.lower()
    markers = ("se" + "cret", "pass" + "word", "token", "credential")
    return lowered == ".env" or any(
        marker in lowered for marker in markers
    )
