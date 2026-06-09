from pathlib import Path

from trading_bot.mt5.safety import find_mt5_prohibited_patterns

MT5_PROHIBITED_TERMS = (
    "order_send",
    "order_check",
    "account_info",
    "positions_get",
)


def test_mt5_scanner_finds_no_execution_patterns_in_source() -> None:
    assert find_mt5_prohibited_patterns(Path("src") / "trading_bot") == []


def test_mt5_execution_terms_are_only_in_allowed_contexts() -> None:
    allowed_prefixes = ("docs", "tests")
    allowed_source_files = {
        Path("src/trading_bot/audit/code_scan.py"),
        Path("src/trading_bot/mt5/demo_execution.py"),
        Path("src/trading_bot/mt5/safety.py"),
    }
    allowed_top_level_docs = {
        Path("README.md"),
        Path("SAFETY.md"),
    }
    allowed_config_files = {
        Path("config/mt5_transformation.yaml"),
    }
    violations: list[str] = []
    for path in _iter_text_files(Path(".")):
        normalized = Path(*path.parts)
        text = path.read_text(encoding="utf-8", errors="ignore")
        if not any(term in text for term in MT5_PROHIBITED_TERMS):
            continue
        if (
            normalized in allowed_source_files
            or normalized in allowed_config_files
            or normalized in allowed_top_level_docs
        ):
            continue
        if normalized.parts and normalized.parts[0] in allowed_prefixes:
            continue
        violations.append(str(normalized))

    assert violations == []


def _iter_text_files(root: Path):
    suffixes = {".py", ".md", ".yaml", ".yml", ".txt"}
    ignored_parts = {".pytest_cache", ".ruff_cache", "__pycache__", "data", "tmp"}
    for path in root.rglob("*"):
        if any(part in ignored_parts for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in suffixes:
            yield path
