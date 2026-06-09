from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.parse_strategy_tester_report import parse_strategy_tester_report

DEFAULT_OUTPUT_ROOT = Path("data/processed/strategy_tester_evidence")
SECRET_NAME_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|credential|login|private|\.env)",
    re.IGNORECASE,
)
SECRET_VALUE_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|credential|login)\b\s*[:=]\s*[^\s,;]+"
)
TEXT_SUFFIXES = {".txt", ".log", ".htm", ".html", ".xml", ".csv", ".json", ".set", ".ini"}


@dataclass(frozen=True)
class EvidenceItem:
    name: str
    status: str
    path: str = ""
    message: str = ""


@dataclass(frozen=True)
class StrategyTesterEvidenceCollectionResult:
    status: str
    run_id: str
    package_dir: str
    manifest_path: str
    parser_summary_path: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def collect_strategy_tester_evidence(
    *,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    run_id: str | None = None,
    tester_artifacts: Sequence[str | Path] | None = None,
    settings_file: str | Path | None = None,
    settings_summary: str | Path | None = None,
    compile_log: str | Path | None = None,
    source_scan: str | Path | None = None,
    simulated_execution: bool = False,
) -> StrategyTesterEvidenceCollectionResult:
    selected_run_id = run_id or datetime.now(UTC).strftime("strategy_tester_%Y%m%dT%H%M%SZ")
    package_dir = Path(output_root).resolve() / selected_run_id
    package_dir.mkdir(parents=True, exist_ok=True)
    missing: list[str] = []
    skipped: list[str] = []
    evidence: list[EvidenceItem] = []

    tester_sources = [Path(path) for path in tester_artifacts or []]
    discovered_settings_file = settings_file or _discover_first_file(tester_sources, {".set"})
    discovered_settings_summary = settings_summary or _discover_summary_json(tester_sources)
    evidence.append(
        _copy_optional_paths(
            sources=tester_sources,
            destination=package_dir / "tester_artifacts",
            name="tester_artifacts",
            missing=missing,
            skipped=skipped,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=discovered_settings_file,
            destination=package_dir / "settings",
            name="settings_file",
            missing=missing,
            skipped=skipped,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=discovered_settings_summary,
            destination=package_dir / "settings_summary",
            name="settings_summary",
            missing=missing,
            skipped=skipped,
            append_missing=settings_summary is not None,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=compile_log,
            destination=package_dir / "compile_log",
            name="compile_log",
            missing=missing,
            skipped=skipped,
        )
    )
    evidence.append(
        _copy_optional_path(
            source=source_scan,
            destination=package_dir / "source_scan",
            name="source_scan",
            missing=missing,
            skipped=skipped,
        )
    )

    parser_result = parse_strategy_tester_report(
        package_dir / "tester_artifacts",
        monitor_only=not simulated_execution,
    )
    parser_summary_path = package_dir / "parser_summary.json"
    parser_summary_path.write_text(
        json.dumps(parser_result.to_dict(), indent=2),
        encoding="utf-8",
    )
    evidence.append(
        EvidenceItem(
            "parser_summary",
            parser_result.status,
            str(parser_summary_path),
            parser_result.message,
        )
    )

    evidence_kind = (
        "strategy_tester_simulated_execution_research_evidence"
        if simulated_execution
        else "monitor_only_tester_evidence"
    )
    manifest = {
        "package_type": "strategy_tester_evidence",
        "evidence_kind": evidence_kind,
        "run_id": selected_run_id,
        "created_at_utc": datetime.now(UTC).isoformat(),
        "monitor_only": not simulated_execution,
        "simulated_execution": simulated_execution,
        "trading_approval": False,
        "formal_trial_evidence": False,
        "trial_evidence_skipped": True,
        "strategy_tester_evidence": True,
        "surge_2_step_blocked": True,
        "vanguard_blocked": True,
        "credentials_collected": False,
        "evidence": [asdict(item) for item in evidence],
        "missing": missing,
        "skipped": skipped,
    }
    manifest_path = package_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (package_dir / "README.md").write_text(
        _render_readme(selected_run_id, evidence_kind=evidence_kind),
        encoding="utf-8",
    )

    if parser_result.status == "FAIL":
        status = "FAIL"
    elif missing or skipped or parser_result.status == "WARN":
        status = "WARN"
    else:
        status = "PASS"
    return StrategyTesterEvidenceCollectionResult(
        status=status,
        run_id=selected_run_id,
        package_dir=str(package_dir),
        manifest_path=str(manifest_path),
        parser_summary_path=str(parser_summary_path),
        evidence=evidence,
        missing=missing,
        skipped=skipped,
    )


def _discover_first_file(sources: Sequence[Path], suffixes: set[str]) -> Path | None:
    for source in sources:
        if not source.exists():
            continue
        candidates = [source] if source.is_file() else sorted(source.rglob("*"))
        for candidate in candidates:
            if (
                candidate.is_file()
                and candidate.suffix.lower() in suffixes
                and not _is_secret_like(candidate)
            ):
                return candidate
    return None


def _discover_summary_json(sources: Sequence[Path]) -> Path | None:
    summary_names = (
        "summary.json",
        "settings_summary.json",
        "strategy_tester_summary.json",
        "parser_summary.json",
    )
    for source in sources:
        if not source.exists():
            continue
        candidates = [source] if source.is_file() else sorted(source.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix.lower() != ".json":
                continue
            if _is_secret_like(candidate):
                continue
            lowered = candidate.name.lower()
            if lowered in summary_names or lowered.endswith(".summary.json"):
                return candidate
    return None


def _copy_optional_paths(
    *,
    sources: Sequence[Path],
    destination: Path,
    name: str,
    missing: list[str],
    skipped: list[str],
) -> EvidenceItem:
    if not sources:
        missing.append(name)
        return EvidenceItem(name, "MISSING", message="path not provided")
    collected = 0
    for source in sources:
        item = _copy_optional_path(
            source=source,
            destination=destination,
            name=name,
            missing=missing,
            skipped=skipped,
            append_missing=False,
        )
        if item.status == "COLLECTED":
            collected += int(item.message.removeprefix("files=") or 0)
    if collected <= 0:
        if name not in missing:
            missing.append(name)
        return EvidenceItem(name, "MISSING", str(destination), "no files collected")
    return EvidenceItem(name, "COLLECTED", str(destination), f"files={collected}")


def _copy_optional_path(
    *,
    source: str | Path | None,
    destination: Path,
    name: str,
    missing: list[str],
    skipped: list[str],
    append_missing: bool = True,
) -> EvidenceItem:
    if source is None:
        if append_missing:
            missing.append(name)
        return EvidenceItem(name, "MISSING", message="path not provided")
    source_path = Path(source)
    if not source_path.exists():
        if append_missing:
            missing.append(name)
        return EvidenceItem(name, "MISSING", str(source_path), "path does not exist")
    if _is_secret_like(source_path):
        skipped.append(name)
        return EvidenceItem(name, "SKIPPED", str(source_path), "secret-like path excluded")

    destination.mkdir(parents=True, exist_ok=True)
    copied: list[Path | None]
    if source_path.is_dir():
        copied = [
            _copy_file(path, destination / path.relative_to(source_path), skipped)
            for path in source_path.rglob("*")
            if path.is_file()
        ]
    else:
        copied = [_copy_file(source_path, destination / source_path.name, skipped)]
    kept = [path for path in copied if path]
    if not kept:
        if append_missing:
            missing.append(name)
        return EvidenceItem(name, "MISSING", str(destination), "all files were excluded")
    return EvidenceItem(name, "COLLECTED", str(destination), f"files={len(kept)}")


def _copy_file(source: Path, destination: Path, skipped: list[str]) -> Path | None:
    if _is_secret_like(source):
        skipped.append(str(source))
        return None
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() in TEXT_SUFFIXES:
        try:
            text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            shutil.copy2(source, destination)
            return destination
        destination.write_text(_redact_text(text), encoding="utf-8")
        return destination
    shutil.copy2(source, destination)
    return destination


def _is_secret_like(path: Path) -> bool:
    return SECRET_NAME_RE.search(path.name) is not None


def _redact_text(text: str) -> str:
    return SECRET_VALUE_RE.sub(lambda match: f"{match.group(1)}=<REDACTED>", text)


def _render_readme(run_id: str, *, evidence_kind: str) -> str:
    return "\n".join(
        [
            "# Strategy Tester Evidence",
            "",
            f"- Run ID: {run_id}",
            f"- Evidence kind: {evidence_kind}",
            "- Formal Trial observation evidence: false",
            "- Trading approval: false",
            "- Surge 2 Step: blocked",
            "- Vanguard: blocked",
            "",
            "This package is local Strategy Tester evidence only. It does not approve "
            "Trial trading, Surge 2 Step, Vanguard, Challenge, Verification, Funded, "
            "live use, or profitability claims. Simulated execution evidence is "
            "research-only backtest evidence.",
            "",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect local MT5 Strategy Tester evidence.")
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT), help="Output root.")
    parser.add_argument("--run-id", help="Optional deterministic run ID.")
    parser.add_argument(
        "--tester-artifacts",
        action="append",
        help="Tester report/log file or directory. Repeat for multiple paths.",
    )
    parser.add_argument("--settings-file", help="Safe .set file used for the tester run.")
    parser.add_argument("--settings-summary", help="Optional generated settings summary JSON.")
    parser.add_argument("--compile-log", help="MetaEditor compile log.")
    parser.add_argument("--source-scan", help="MQL5 source scan JSON.")
    parser.add_argument(
        "--simulated-execution",
        action="store_true",
        help=(
            "Package Strategy Tester simulated execution research evidence. "
            "Without this flag, tester artifacts are treated as monitor-only evidence."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = collect_strategy_tester_evidence(
        output_root=args.output_root,
        run_id=args.run_id,
        tester_artifacts=args.tester_artifacts,
        settings_file=args.settings_file,
        settings_summary=args.settings_summary,
        compile_log=args.compile_log,
        source_scan=args.source_scan,
        simulated_execution=args.simulated_execution,
    )
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"strategy_tester_evidence_collection: {result.status}")
        print(f"run_id: {result.run_id}")
        print(f"package_dir: {result.package_dir}")
        if result.missing:
            print("missing: " + ", ".join(result.missing))
        print("Collection is local research evidence; it does not approve trading.")
    return 1 if result.status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
