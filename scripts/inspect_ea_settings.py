from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

SECRET_KEY_PARTS = ("password", "passwd", "secret", "token", "key", "credential", "login")
IMPORTANT_KEYS = (
    "EnableTrading",
    "EnableTrialExecution",
    "StrategyTesterExecutionMode",
    "EnablePropChallengeMode",
    "AccountProgram",
    "AccountStage",
    "AllowedSymbols",
    "StrategySelection",
    "StrategyTimeframe",
    "BrokerServerUtcOffsetMinutes",
    "MinHoldSeconds",
    "StopLossRequired",
)


def inspect_settings_file(path: str | Path) -> dict[str, Any]:
    set_path = Path(path)
    if not set_path.exists():
        return {
            "status": "FAIL",
            "set_path": str(set_path),
            "message": "settings file missing",
            "settings": {},
            "failures": ["settings_file_missing"],
            "warnings": [],
        }

    settings = _parse_set_file(set_path)
    summary_path = set_path.with_suffix(".summary.json")
    summary = _read_summary(summary_path)
    failures = _settings_failures(set_path, settings, summary)
    warnings: list[str] = []
    if not summary:
        warnings.append("summary_json_missing_or_unreadable")
    status = "FAIL" if failures else ("WARN" if warnings else "PASS")
    return {
        "status": status,
        "set_path": str(set_path),
        "summary_json_path": str(summary_path) if summary_path.exists() else "",
        "summary_preset_name": summary.get("preset_name", ""),
        "settings": {
            key: _redact_if_secret(key, settings.get(key, ""))
            for key in IMPORTANT_KEYS
            if key in settings
        },
        "failures": failures,
        "warnings": warnings,
        "message": (
            "settings inspection passed"
            if status == "PASS"
            else "settings inspection found items requiring review"
        ),
    }


def _parse_set_file(path: Path) -> dict[str, str]:
    settings: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        settings[key.strip()] = value.strip()
    return settings


def _read_summary(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _settings_failures(
    set_path: Path,
    settings: dict[str, str],
    summary: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    strategy_selection = settings.get("StrategySelection", "")
    preset_hint = " ".join(
        [
            set_path.name.lower(),
            str(summary.get("preset_name", "")).lower(),
        ]
    )
    if "vwap" in preset_hint and strategy_selection == "STRATEGY_OPENING_RANGE_BREAKOUT":
        failures.append("vwap_preset_selects_orb")
    if "orb" in preset_hint and strategy_selection == "STRATEGY_VWAP_TREND_CONTINUATION":
        failures.append("orb_preset_selects_vwap")

    if settings.get("StrategyTesterExecutionMode", "").lower() == "true":
        expected_false = (
            "EnableTrading",
            "EnableTrialExecution",
            "EnablePropChallengeMode",
        )
        for key in expected_false:
            if settings.get(key, "").lower() != "false":
                failures.append(f"strategy_tester_requires_{key}_false")
        if settings.get("AccountStage") != "ACCOUNT_STAGE_MONITOR_ONLY":
            failures.append("strategy_tester_requires_monitor_only_stage")
        if settings.get("AllowedSymbols") != "EURUSD":
            failures.append("strategy_tester_requires_eurusd")
    return failures


def _redact_if_secret(key: str, value: str) -> str:
    lowered = key.lower()
    if any(part in lowered for part in SECRET_KEY_PARTS):
        return "<redacted>"
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect a local MQL5 EA .set file without opening MT5."
    )
    parser.add_argument("path", help="Path to the .set file.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = inspect_settings_file(args.path)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"ea_settings_inspect: {result['status']}")
        print(result["message"])
        print(f"set_path: {result['set_path']}")
        if result.get("summary_json_path"):
            print(f"summary_json_path: {result['summary_json_path']}")
        print(f"settings: {result['settings']}")
        if result["failures"]:
            print(f"failures: {result['failures']}")
        if result["warnings"]:
            print(f"warnings: {result['warnings']}")
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
