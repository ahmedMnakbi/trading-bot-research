from __future__ import annotations

from pathlib import Path

MT5_PROHIBITED_PATTERNS = (
    "order" + "_send",
    "order" + "_check",
    "account" + "_info",
    "positions" + "_get",
)
PYTHON_MT5_EXECUTION_IMPORT_PATTERNS = (
    "trading_bot.mt5.demo_execution",
    "from trading_bot.mt5 import demo_execution",
)

DEFAULT_ALLOWED_PARTS = {"docs", "tests"}
QUARANTINED_LEGACY_FILES = {
    Path("mt5/demo_execution.py"),
    Path("src/trading_bot/mt5/demo_execution.py"),
}
DEFAULT_ALLOWED_FILES = {
    Path("mt5/safety.py"),
    Path("src/trading_bot/mt5/safety.py"),
    Path("audit/code_scan.py"),
    Path("src/trading_bot/audit/code_scan.py"),
}
MQL5_SUFFIXES = {".mq5", ".mqh"}
MQL5_ALLOWED_ORDER_CALL_FILES = {
    Path("Include/UpcomersNYSessionPropBot/TrialExecution.mqh"),
    Path("Include/UpcomersNYSessionPropBot/TesterExecution.mqh"),
}
MQL5_BANNED_TERMS = {
    "grid": "grid_trading",
    "martingale": "martingale",
    "averaging down": "averaging_down",
    "averagedown": "averaging_down",
    "hft": "hft",
    "high-frequency": "hft",
    "arbitrage": "arbitrage",
    "copy trading": "copy_trading",
    "copytrade": "copy_trading",
    "scalping under 2": "sub_2_minute_scalping",
    "scalpingunder2minutes": "sub_2_minute_scalping",
    "tick scalping": "tick_scalping",
}
MQL5_FORBIDDEN_ORDER_PATTERNS = {
    "ordersend(": "mql5_order_send",
    "ctrade": "mql5_ctrade",
    ".buy(": "mql5_buy_call",
    ".sell(": "mql5_sell_call",
    "positionopen(": "mql5_position_open",
    "buylimit(": "mql5_buy_limit",
    "selllimit(": "mql5_sell_limit",
    "buystop(": "mql5_buy_stop",
    "sellstop(": "mql5_sell_stop",
}
MQL5_REQUIRED_CONTROL_TOKENS = {
    "phase5_config_validation": ("validatephase5complianceconfig",),
    "phase6_strategy_signal_types": (
        "signal_wait",
        "signal_setup_forming",
        "signal_enter_long_intent",
        "signal_enter_short_intent",
        "signal_exit_intent",
        "signal_skip_session",
        "signal_skip_spread",
        "signal_skip_news",
        "signal_skip_data",
        "signal_session_close",
    ),
    "entry_intent_stop_loss_guard": (
        "entryintenthasrequiredstoploss",
        "suggestedstoploss",
        "setentryintentdecision",
    ),
    "strategy_session_gating": ("isentrysessionforsymbol", "signal_skip_session"),
    "strategy_cooldown_guard": ("orb_signal_cooldown", "vwap_signal_cooldown"),
    "manual_confirmation_guard": ("manualconfirmation",),
    "account_stage_guard": ("accountstage", "isprotectedaccountstage"),
    "account_program_guard": ("accountprogram", "accountprogramtostring"),
    "approval_metadata_guard": (
        "accountprogramrulesreviewid",
        "trialevidenceid",
        "sourcescanpassid",
        "compilepassid",
        "finalauditpackageid",
        "humanapprovalid",
    ),
    "prop_day_reset_timezone_guard": ("propdayresettimezone",),
    "dynamic_risk_shield_guard": ("dynamicriskshield",),
    "unknown_rule_block_status": ("unknown_rule_block",),
    "trading_disabled_default": ("enabletrading", "false"),
    "trial_execution_disabled_default": ("enabletrialexecution", "false"),
    "trial_execution_gate": (
        "validatetrialexecutionconfig",
        "trialriskfree",
        "i_accept_trial_risk_free_execution_only",
        "sourcescanpassid",
        "allowedsymbols",
    ),
    "stop_loss_required_guard": ("stoplossrequired",),
    "minimum_hold_guard": ("minholdseconds",),
    "daily_trade_counter": ("maxtradesperday",),
    "trade_action_counter": ("recordtradeactionrequest",),
    "server_message_counter": ("maxservermessagesperday",),
    "daily_loss_guard": ("maxdailyloss",),
    "overall_loss_guard": ("maxoverallloss",),
    "trade_manager_no_trade": ("refuseexecution", "no-trade"),
}


def find_mt5_prohibited_patterns(
    root: str | Path = ".",
    *,
    allowed_parts: set[str] | None = None,
    allowed_files: set[Path] | None = None,
) -> list[dict[str, object]]:
    root_path = Path(root)
    selected_allowed_parts = allowed_parts or DEFAULT_ALLOWED_PARTS
    selected_allowed_files = allowed_files or DEFAULT_ALLOWED_FILES
    matches: list[dict[str, object]] = []
    for path in _iter_text_files(root_path):
        relative = _relative(path, root_path)
        if _is_allowed(relative, selected_allowed_parts, selected_allowed_files):
            continue
        if _is_quarantined_legacy_file(relative, root_path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()
            for pattern in MT5_PROHIBITED_PATTERNS:
                if pattern in lowered:
                    matches.append(
                        {
                            "path": str(relative),
                            "line": line_number,
                            "pattern": pattern,
                        }
                    )
            for pattern in PYTHON_MT5_EXECUTION_IMPORT_PATTERNS:
                if pattern in lowered:
                    matches.append(
                        {
                            "path": str(relative),
                            "line": line_number,
                            "pattern": "python_mt5_execution_import",
                        }
                    )
    return matches


def assert_mt5_read_only_source(root: str | Path = ".") -> None:
    matches = find_mt5_prohibited_patterns(root)
    if matches:
        details = ", ".join(
            f"{match['path']}:{match['line']} {match['pattern']}" for match in matches
        )
        raise ValueError(f"MT5 prohibited execution/account patterns found: {details}")


def find_mql5_source_scan_violations(root: str | Path = ".") -> list[dict[str, object]]:
    root_path = Path(root)
    files = list(_iter_mql5_files(root_path))
    if not files:
        return []
    violations: list[dict[str, object]] = []
    combined_text_parts: list[str] = []
    for path in files:
        relative = _relative(path, root_path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        combined_text_parts.extend(lines)
        for line_number, line in enumerate(lines, start=1):
            lowered = line.lower()
            compact = "".join(lowered.split())
            for term, pattern in MQL5_FORBIDDEN_ORDER_PATTERNS.items():
                if term in compact and relative not in MQL5_ALLOWED_ORDER_CALL_FILES:
                    violations.append(
                        {
                            "path": str(relative),
                            "line": line_number,
                            "pattern": pattern,
                        }
                    )
            for term, pattern in MQL5_BANNED_TERMS.items():
                if term in lowered and not _is_mql5_banned_term_allowlisted(lowered, term):
                    violations.append(
                        {
                            "path": str(relative),
                            "line": line_number,
                            "pattern": pattern,
                        }
                    )
    combined = "\n".join(combined_text_parts).lower()
    for pattern, tokens in MQL5_REQUIRED_CONTROL_TOKENS.items():
        if not all(token in combined for token in tokens):
            violations.append({"path": str(root_path), "line": 0, "pattern": pattern})
    return violations


def _iter_text_files(root: Path):
    suffixes = {".py", ".md", ".yaml", ".yml", ".txt"}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in suffixes:
            yield path


def _iter_mql5_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in MQL5_SUFFIXES:
            yield path


def _is_allowed(path: Path, allowed_parts: set[str], allowed_files: set[Path]) -> bool:
    normalized = Path(*path.parts)
    if normalized in allowed_files:
        return True
    return any(part in allowed_parts for part in normalized.parts)


def _is_quarantined_legacy_file(path: Path, root: Path) -> bool:
    normalized = Path(*path.parts)
    if normalized not in QUARANTINED_LEGACY_FILES:
        return False
    absolute = root / normalized
    try:
        text = absolute.read_text(encoding="utf-8")
    except OSError:
        return False
    return "LEGACY_NON_PROP_COMPATIBLE_QUARANTINE = True" in text


def _is_mql5_banned_term_allowlisted(lowered_line: str, term: str) -> bool:
    compact = "".join(lowered_line.split())
    if term == "grid" and (
        "allowgrid=false" in compact or "allowgrid;" in compact or "config.allowgrid" in compact
    ):
        return True
    if term == "martingale" and (
        "allowmartingale=false" in compact
        or "allowmartingale;" in compact
        or "config.allowmartingale" in compact
    ):
        return True
    if term in {"averaging down", "averagedown"} and (
        "allowaveragingdown=false" in compact
        or "allowaveragingdown;" in compact
        or "config.allowaveragingdown" in compact
    ):
        return True
    if term in {"hft", "high-frequency"} and (
        "allowhft=false" in compact or "allowhft;" in compact or "config.allowhft" in compact
    ):
        return True
    if term == "arbitrage" and (
        "allowarbitrage=false" in compact
        or "allowarbitrage;" in compact
        or "config.allowarbitrage" in compact
    ):
        return True
    if term in {"copy trading", "copytrade"} and (
        "allowcopytrading=false" in compact
        or "allowcopytrading;" in compact
        or "config.allowcopytrading" in compact
    ):
        return True
    if (
        "allowscalpingunder2minutes=false" in compact
        or "allowscalpingunder2minutes;" in compact
        or "config.allowscalpingunder2minutes" in compact
    ):
        return True
    return any(word in lowered_line for word in {"forbidden", "prohibited", "disabled"})


def _relative(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path
