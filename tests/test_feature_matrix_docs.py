from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_feature_matrix_contains_required_rows() -> None:
    text = (ROOT / "docs/feature_matrix.md").read_text(encoding="utf-8")
    for feature in [
        "Config validation",
        "OHLCV ingestion",
        "Portfolio paper trading",
        "Failure injection",
        "Incident replay",
        "Run registry",
        "Real exchange order placement",
        "Authenticated exchange client",
        "Live trading",
        "Optimization",
        "Machine learning",
    ]:
        assert feature in text
    assert "Not implemented and not approved" in text


def test_release_notes_and_changelog_include_non_live_limitations() -> None:
    release_notes = (ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "not approved for real-money trading" in release_notes
    assert "0.1.0-rc1" in changelog
