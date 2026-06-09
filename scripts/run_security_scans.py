from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.mt5.safety import find_mt5_prohibited_patterns


@dataclass(frozen=True)
class SecurityScanResult:
    name: str
    status: str
    message: str
    command: list[str] = field(default_factory=list)


def local_semgrep_config(root: Path) -> Path | None:
    candidates = [root / "semgrep.yml", root / ".semgrep.yml", root / ".semgrep"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def run_command_scan(name: str, command: list[str], strict: bool) -> SecurityScanResult:
    if shutil.which(command[0]) is None:
        status = "FAIL" if strict else "SKIPPED"
        return SecurityScanResult(name, status, f"{command[0]} not installed", command)
    result = subprocess.run(command, check=False)
    status = "PASS" if result.returncode == 0 else "FAIL"
    return SecurityScanResult(name, status, f"exit_code={result.returncode}", command)


def run_security_scans(
    project_root: str | Path = ".",
    *,
    strict: bool = False,
) -> list[SecurityScanResult]:
    root = Path(project_root).resolve()
    results: list[SecurityScanResult] = []
    mt5_matches = find_mt5_prohibited_patterns(root / "src" / "trading_bot")
    results.append(
        SecurityScanResult(
            "python_mt5_execution_scan",
            "PASS" if not mt5_matches else "FAIL",
            "no prop-compatible Python MT5 execution patterns found"
            if not mt5_matches
            else f"{len(mt5_matches)} prohibited patterns found",
        )
    )
    results.append(
        run_command_scan(
            "gitleaks",
            ["gitleaks", "detect", "--source", str(root), "--no-git", "--redact", "-v"],
            strict,
        )
    )
    results.append(run_command_scan("pip-audit", ["pip-audit"], strict))
    semgrep_config = local_semgrep_config(root)
    if semgrep_config is None:
        results.append(
            SecurityScanResult(
                "semgrep",
                "FAIL" if strict else "SKIPPED",
                "no local semgrep config found; cloud/auto config was not used",
            )
        )
    else:
        results.append(
            run_command_scan(
                "semgrep",
                [
                    "semgrep",
                    "scan",
                    "--config",
                    str(semgrep_config),
                    "--metrics=off",
                    "--disable-version-check",
                ],
                strict,
            )
        )
    return results


def overall_status(results: Sequence[SecurityScanResult]) -> str:
    if any(result.status == "FAIL" for result in results):
        return "FAIL"
    if any(result.status == "SKIPPED" for result in results):
        return "WARN"
    return "PASS"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run local-only project security scans.")
    parser.add_argument("--project-root", default=".", help="Repository root.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat missing optional tools as failures.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    results = run_security_scans(args.project_root, strict=args.strict)
    status = overall_status(results)
    payload = {"status": status, "scans": [asdict(result) for result in results]}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"security_scans: {status}")
        for result in results:
            print(f"{result.status}\t{result.name}\t{result.message}")
        print("Scans are local-only; semgrep cloud/auto config and source upload are not used.")
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
