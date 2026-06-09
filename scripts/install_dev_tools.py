from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass

DEV_MODULES = {
    "pytest": "pytest",
    "ruff": "ruff",
}
OPTIONAL_MODULES = {
    "pre-commit": "pre_commit",
    "semgrep": "semgrep",
    "pip-audit": "pip_audit",
}


@dataclass(frozen=True)
class ToolStatus:
    name: str
    status: str
    message: str


def module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def check_tools(include_optional: bool = True) -> list[ToolStatus]:
    results = [
        ToolStatus(name, "PASS" if module_available(module) else "MISSING", "Python module check")
        for name, module in DEV_MODULES.items()
    ]
    if include_optional:
        results.extend(
            ToolStatus(
                name,
                "PASS" if module_available(module) else "OPTIONAL_MISSING",
                "optional local tool",
            )
            for name, module in OPTIONAL_MODULES.items()
        )
    return results


def install_tools(include_optional: bool, allow_current_python: bool) -> int:
    if not allow_current_python and sys.prefix == sys.base_prefix:
        print(
            "Refusing to install into the global/current Python without --allow-current-python. "
            "Create a project virtual environment first."
        )
        return 2
    commands = [[sys.executable, "-m", "pip", "install", "-e", ".[dev]"]]
    if include_optional:
        commands.append([sys.executable, "-m", "pip", "install", *OPTIONAL_MODULES.keys()])
    for command in commands:
        print(f"==> {' '.join(command)}")
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify or install project-local Python development tools."
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install tools into the active Python environment.",
    )
    parser.add_argument(
        "--no-optional",
        action="store_true",
        help="Do not check/install optional pre-commit, semgrep, and pip-audit tools.",
    )
    parser.add_argument(
        "--allow-current-python",
        action="store_true",
        help="Permit installation into the current Python when it is not a virtual environment.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    include_optional = not args.no_optional
    if args.install:
        code = install_tools(include_optional, args.allow_current_python)
        if code != 0:
            return code
    results = check_tools(include_optional=include_optional)
    print("development_tools:")
    for result in results:
        print(f"{result.status}\t{result.name}\t{result.message}")
    missing_optional = [result.name for result in results if result.status == "OPTIONAL_MISSING"]
    if missing_optional:
        print(f"optional_missing: {', '.join(missing_optional)}")
        print(
            "next_steps: install optional tools in the project environment if those "
            "scans are needed"
        )
    print(
        "MT5, MetaEditor, prop credentials, and live trading permissions are not "
        "installed by this script."
    )
    return 0 if all(result.status != "MISSING" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
