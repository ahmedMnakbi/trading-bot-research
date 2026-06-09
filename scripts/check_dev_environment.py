from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_bot.config.settings import load_settings

SECRET_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "PASS", "CREDENTIAL", "LOGIN")
REQUIRED_IMPORTS = {
    "pytest": "pytest",
    "ruff": "ruff",
    "pydantic": "pydantic",
    "pydantic_settings": "pydantic_settings",
    "yaml": "PyYAML",
    "typer": "typer",
    "rich": "rich",
    "structlog": "structlog",
    "pandas": "pandas",
    "numpy": "numpy",
    "ccxt": "ccxt",
}
OPTIONAL_TOOLS = {
    "pre-commit": ("pre-commit", "pre_commit"),
    "semgrep": ("semgrep", "semgrep"),
    "pip-audit": ("pip-audit", "pip_audit"),
    "gitleaks": ("gitleaks", None),
}


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    message: str
    details: dict[str, object] = field(default_factory=dict)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def redact_environment(env: Mapping[str, str]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in env.items():
        if any(marker in key.upper() for marker in SECRET_MARKERS):
            redacted[key] = "<redacted>"
        else:
            redacted[key] = value
    return redacted


def detect_system_python_alias() -> CheckResult:
    try:
        result = subprocess.run(
            ["python", "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CheckResult(
            "system_python_alias",
            "WARN",
            "system python is unavailable",
            {"error": str(exc)},
        )
    output = f"{result.stdout}\n{result.stderr}".strip()
    lowered = output.lower()
    if result.returncode != 0 or "python was not found" in lowered or "microsoft store" in lowered:
        return CheckResult(
            "system_python_alias",
            "WARN",
            "system python alias appears unavailable or broken",
            {"output": output},
        )
    return CheckResult("system_python_alias", "PASS", output or "python command works")


def detect_codex_python(current_executable: str = sys.executable) -> CheckResult:
    executable = Path(current_executable)
    bundled = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "python"
        / "python.exe"
    )
    if "codex-primary-runtime" in str(executable):
        return CheckResult(
            "codex_python",
            "PASS",
            "running under bundled Codex Python",
            {"path": str(executable)},
        )
    if bundled.exists():
        return CheckResult(
            "codex_python",
            "PASS",
            "bundled Codex Python detected",
            {"path": str(bundled)},
        )
    return CheckResult("codex_python", "SKIPPED", "bundled Codex Python not detected")


def check_python_version() -> CheckResult:
    version = sys.version_info
    status = "PASS" if version >= (3, 11) else "FAIL"
    return CheckResult(
        "python_version",
        status,
        f"{version.major}.{version.minor}.{version.micro}",
        {"executable": sys.executable},
    )


def check_required_imports() -> list[CheckResult]:
    results: list[CheckResult] = []
    for import_name, package_name in REQUIRED_IMPORTS.items():
        if importlib.util.find_spec(import_name) is None:
            results.append(
                CheckResult(
                    f"required_python_dependency:{package_name}",
                    "FAIL",
                    "missing required Python dependency",
                )
            )
        else:
            results.append(
                CheckResult(f"required_python_dependency:{package_name}", "PASS", "available")
            )
    return results


def check_optional_tools() -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, (command, module_name) in OPTIONAL_TOOLS.items():
        command_path = shutil.which(command)
        module_available = (
            module_name is not None and importlib.util.find_spec(module_name) is not None
        )
        if command_path or module_available:
            details = {"command": command_path, "python_module": module_available}
            results.append(CheckResult(f"optional_tool:{name}", "PASS", "available", details))
        else:
            results.append(
                CheckResult(
                    f"optional_tool:{name}",
                    "SKIPPED",
                    "optional local tool missing; install project-locally if needed",
                )
            )
    return results


def check_live_trading_disabled(root: Path) -> CheckResult:
    settings = load_settings(root / "config" / "default.yaml")
    unsafe = (
        settings.live_trading_enabled
        or settings.governance.real_orders_allowed
        or settings.governance.private_api_allowed
    )
    return CheckResult(
        "live_trading_disabled",
        "FAIL" if unsafe else "PASS",
        "live trading, real orders, and private API are disabled"
        if not unsafe
        else "unsafe trading gates enabled",
    )


def check_native_ea_documented(root: Path) -> CheckResult:
    paths = [root / "AGENTS.md", root / "docs" / "upcomers_native_ea_direction_lock.md"]
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        return CheckResult(
            "native_mql5_ea_documented",
            "FAIL",
            "missing native EA docs",
            {"missing": missing},
        )
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    required = "native MQL5 Expert Advisor"
    if required.lower() not in text.lower():
        return CheckResult(
            "native_mql5_ea_documented",
            "FAIL",
            "native MQL5 EA path not documented",
        )
    return CheckResult("native_mql5_ea_documented", "PASS", "native MQL5 EA prop path documented")


def run_checks(root: Path | None = None, env: Mapping[str, str] | None = None) -> list[CheckResult]:
    selected_root = root or repo_root()
    selected_env = env or os.environ
    redacted = redact_environment(selected_env)
    secret_like = sum(1 for value in redacted.values() if value == "<redacted>")
    results = [
        check_python_version(),
        detect_system_python_alias(),
        detect_codex_python(),
        CheckResult(
            "environment_redaction",
            "PASS",
            "secret-like environment variable values redacted",
            {"secret_like_keys": secret_like},
        ),
        check_live_trading_disabled(selected_root),
        check_native_ea_documented(selected_root),
    ]
    results.extend(check_required_imports())
    results.extend(check_optional_tools())
    return results


def overall_status(results: Sequence[CheckResult]) -> str:
    if any(result.status == "FAIL" for result in results):
        return "FAIL"
    if any(result.status in {"WARN", "SKIPPED"} for result in results):
        return "WARN"
    return "PASS"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check the project-local development environment.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    results = run_checks()
    status = overall_status(results)
    payload = {"status": status, "checks": [asdict(result) for result in results]}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"development_environment: {status}")
        for result in results:
            print(f"{result.status}\t{result.name}\t{result.message}")
        print(
            "No MT5, MetaEditor, prop credentials, or live trading permissions are "
            "installed or used."
        )
    return 1 if status == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
