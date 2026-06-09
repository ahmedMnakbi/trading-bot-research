from __future__ import annotations

from trading_bot.audit.integrity import verify_artifact_manifest, write_artifact_manifest


def test_manifest_generation_writes_sha256_hashes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    manifest = write_artifact_manifest(tmp_path)

    assert manifest.exists()
    assert "sha256" in manifest.read_text(encoding="utf-8")


def test_manifest_verification_passes_for_unchanged_artifacts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    write_artifact_manifest(tmp_path)

    assert verify_artifact_manifest(tmp_path).status == "PASS"


def test_manifest_verification_fails_when_file_modified(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    write_artifact_manifest(tmp_path)
    (tmp_path / "a.txt").write_text("changed", encoding="utf-8")

    assert verify_artifact_manifest(tmp_path).status == "FAIL"


def test_manifest_verification_fails_when_file_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    file_path = tmp_path / "a.txt"
    file_path.write_text("hello", encoding="utf-8")
    write_artifact_manifest(tmp_path)
    file_path.unlink()

    assert verify_artifact_manifest(tmp_path).status == "FAIL"


def test_manifest_verification_warns_on_extra_files(tmp_path) -> None:  # type: ignore[no-untyped-def]
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    write_artifact_manifest(tmp_path)
    (tmp_path / "b.txt").write_text("extra", encoding="utf-8")

    assert verify_artifact_manifest(tmp_path).status == "WARN"

