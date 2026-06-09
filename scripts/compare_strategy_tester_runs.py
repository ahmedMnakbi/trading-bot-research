from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.parse_strategy_tester_report import parse_strategy_tester_report

COMPARISON_COLUMNS = (
    "symbol",
    "timeframe",
    "strategy",
    "date_range",
    "entry_intents",
    "orders_attempted",
    "orders_sent",
    "trades_deals",
    "net_profit",
    "return_percent",
    "max_drawdown",
    "profit_factor",
    "warnings",
)


@dataclass(frozen=True)
class StrategyTesterComparisonResult:
    status: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    output_json_path: str = ""
    output_md_path: str = ""
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_strategy_tester_runs(
    inputs: Sequence[str | Path],
    *,
    output_json: str | Path | None = None,
    output_md: str | Path | None = None,
) -> StrategyTesterComparisonResult:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for raw_input in inputs:
        input_path = Path(raw_input)
        summary, load_warnings = _load_summary(input_path)
        warnings.extend(load_warnings)
        if summary:
            rows.append(_comparison_row(input_path, summary))

    status = "PASS" if rows else "WARN"
    if not inputs:
        warnings.append("no_inputs_provided")
    if warnings and rows:
        status = "WARN"

    output_json_path = _write_json(output_json, rows, warnings, status)
    output_md_path = _write_markdown(output_md, rows)
    return StrategyTesterComparisonResult(
        status=status,
        rows=rows,
        warnings=warnings,
        output_json_path=str(output_json_path) if output_json_path else "",
        output_md_path=str(output_md_path) if output_md_path else "",
        message=(
            "Strategy Tester comparison generated"
            if rows
            else "No Strategy Tester summaries could be compared"
        ),
    )


def _load_summary(path: Path) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    if not path.exists():
        return {}, [f"missing_input:{path}"]

    if path.is_dir():
        parser_summary = path / "parser_summary.json"
        if parser_summary.exists():
            return _load_json_file(parser_summary)
        tester_artifacts = path / "tester_artifacts"
        parse_target = tester_artifacts if tester_artifacts.exists() else path
        parsed = parse_strategy_tester_report(parse_target, monitor_only=False)
        return parsed.to_dict(), warnings

    if path.suffix.lower() == ".json":
        return _load_json_file(path)

    parsed = parse_strategy_tester_report(path, monitor_only=False)
    return parsed.to_dict(), warnings


def _load_json_file(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"unreadable_json:{path}:{exc}"]
    if not isinstance(loaded, dict):
        return {}, [f"json_not_object:{path}"]
    return loaded, []


def _comparison_row(input_path: Path, summary: dict[str, Any]) -> dict[str, Any]:
    activity_counts = _dict(summary.get("activity_counts"))
    metrics = _dict(summary.get("performance_metrics"))
    diagnostics = _dict(summary.get("strategy_diagnostics"))
    tester_execution = _dict(summary.get("tester_execution_summary"))
    input_settings = _dict(summary.get("input_settings"))

    enter_long = _int_value(diagnostics.get("enter_long"))
    enter_short = _int_value(diagnostics.get("enter_short"))
    tester_entry_intents = _int_value(tester_execution.get("tester_entry_intents_received"))
    entry_intents = tester_entry_intents if tester_entry_intents > 0 else enter_long + enter_short
    trades = _first_present(
        activity_counts.get("trades"),
        metrics.get("total_trades"),
        metrics.get("number_of_trades"),
    )
    deals = _first_present(activity_counts.get("deals"), metrics.get("total_deals"))

    return {
        "input": str(input_path),
        "symbol": summary.get("symbol") or input_settings.get("Symbol", ""),
        "timeframe": summary.get("timeframe") or input_settings.get("StrategyTimeframe", ""),
        "strategy": diagnostics.get("strategy") or input_settings.get("StrategySelection", ""),
        "date_range": summary.get("test_period", ""),
        "entry_intents": entry_intents,
        "orders_attempted": _int_value(tester_execution.get("tester_orders_attempted")),
        "orders_sent": _int_value(tester_execution.get("tester_orders_sent_success")),
        "trades_deals": f"{_display_value(trades)}/{_display_value(deals)}",
        "net_profit": _display_value(metrics.get("net_profit")),
        "return_percent": _display_value(metrics.get("return_percent")),
        "max_drawdown": _display_value(
            metrics.get("max_drawdown") or metrics.get("drawdown")
        ),
        "profit_factor": _display_value(metrics.get("profit_factor")),
        "warnings": "; ".join(str(item) for item in summary.get("warnings", [])),
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return ""


def _display_value(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def _write_json(
    output_json: str | Path | None,
    rows: list[dict[str, Any]],
    warnings: list[str],
    status: str,
) -> Path | None:
    if output_json is None:
        return None
    path = Path(output_json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": status,
                "rows": rows,
                "warnings": warnings,
                "trading_approval": False,
                "research_only": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def _write_markdown(output_md: str | Path | None, rows: list[dict[str, Any]]) -> Path | None:
    if output_md is None:
        return None
    path = Path(output_md)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_render_markdown(rows), encoding="utf-8")
    return path


def _render_markdown(rows: list[dict[str, Any]]) -> str:
    header = "| " + " | ".join(COMPARISON_COLUMNS) + " |"
    divider = "| " + " | ".join("---" for _ in COMPARISON_COLUMNS) + " |"
    body = [
        "| "
        + " | ".join(_escape_markdown_cell(row.get(column, "")) for column in COMPARISON_COLUMNS)
        + " |"
        for row in rows
    ]
    lines = [
        "# Strategy Tester Run Comparison",
        "",
        "Research-only Strategy Tester comparison. This is not Trial, Surge 2 Step, "
        "Vanguard, Challenge, Verification, Funded, or live-money approval.",
        "",
        header,
        divider,
        *body,
        "",
    ]
    return "\n".join(lines)


def _escape_markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare local MT5 Strategy Tester parsed reports or evidence folders."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Parsed JSON report, evidence folder, or raw tester report/log.",
    )
    parser.add_argument("--output-json", help="Optional comparison JSON output path.")
    parser.add_argument("--output-md", help="Optional Markdown table output path.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = compare_strategy_tester_runs(
        args.inputs,
        output_json=args.output_json,
        output_md=args.output_md,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"strategy_tester_comparison: {result.status}")
        print(result.message)
        print(f"rows: {len(result.rows)}")
        if result.output_md_path:
            print(f"markdown: {result.output_md_path}")
        if result.output_json_path:
            print(f"json: {result.output_json_path}")
        if result.warnings:
            print("warnings: " + ", ".join(result.warnings))
        print("Comparison is local research only; it does not approve trading.")
    return 1 if result.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
