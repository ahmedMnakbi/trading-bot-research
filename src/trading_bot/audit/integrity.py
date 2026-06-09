from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from trading_bot.audit.models import ScanResult

MANIFEST_NAME = "artifact_manifest.json"


def write_artifact_manifest(artifact_dir: str | Path) -> Path:
    directory = Path(artifact_dir)
    if not directory.exists():
        raise ValueError(f"artifact directory missing: {directory}")
    files = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name == MANIFEST_NAME:
            continue
        rel = path.relative_to(directory).as_posix()
        files.append({"path": rel, "sha256": _sha256(path), "size_bytes": path.stat().st_size})
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "artifact_dir": str(directory),
        "files": files,
    }
    manifest_path = directory / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def verify_artifact_manifest(artifact_dir: str | Path) -> ScanResult:
    directory = Path(artifact_dir)
    manifest_path = directory / MANIFEST_NAME
    if not manifest_path.exists():
        return ScanResult(status="FAIL", failures=["manifest missing"])
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ScanResult(status="FAIL", failures=["malformed manifest"])
    expected = {item["path"]: item for item in manifest.get("files", []) if isinstance(item, dict)}
    failures: list[str] = []
    warnings: list[str] = []
    for rel, item in expected.items():
        path = directory / rel
        if not path.exists():
            failures.append(f"missing file: {rel}")
            continue
        if _sha256(path) != item.get("sha256") or path.stat().st_size != item.get("size_bytes"):
            failures.append(f"modified file: {rel}")
    actual = {
        path.relative_to(directory).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and path.name != MANIFEST_NAME
    }
    extra = actual.difference(expected)
    for rel in sorted(extra):
        warnings.append(f"extra file: {rel}")
    return ScanResult(
        status="FAIL" if failures else ("WARN" if warnings else "PASS"),
        failures=failures,
        warnings=warnings,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as input_file:
        for chunk in iter(lambda: input_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
