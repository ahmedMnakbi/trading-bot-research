from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def index_artifacts(
    run_dir: Path,
    *,
    max_size_bytes: int = 100_000_000,
) -> tuple[list[dict[str, Any]], list[str]]:
    artifacts = []
    warnings = []
    for path in sorted(item for item in run_dir.rglob("*") if item.is_file()):
        if _skip_sensitive_named(path):
            warnings.append(f"skipped sensitive-named file: {path.name}")
            continue
        relative = path.relative_to(run_dir)
        size = path.stat().st_size
        record = {
            "relative_path": relative.as_posix(),
            "size_bytes": size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(),
            "artifact_kind": artifact_kind(path),
        }
        if size > max_size_bytes:
            record["sha256"] = None
            warnings.append(f"skipped large file hash: {relative.as_posix()}")
        else:
            record["sha256"] = sha256_file(path)
        artifacts.append(record)
    return artifacts, warnings


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_kind(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if name == "artifact_manifest.json":
        return "manifest"
    if name == "config_snapshot.yaml" or suffix in {".yaml", ".yml"}:
        return "config_snapshot"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".json":
        return "json"
    if suffix == ".parquet":
        return "parquet"
    if suffix == ".md":
        return "markdown_report"
    if suffix == ".html":
        return "html_report"
    return "other"


def _skip_sensitive_named(path: Path) -> bool:
    lowered = path.name.lower()
    markers = ("se" + "cret", "pass" + "word", "token", "credential")
    return lowered == ".env" or any(
        marker in lowered for marker in markers
    )
