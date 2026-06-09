from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

from scripts.generate_fixture_data import generate_fixtures
from trading_bot.audit.reporting import run_safety_audit
from trading_bot.config.settings import Settings, load_settings
from trading_bot.release.verify import ReleaseVerificationError, verify_release_candidate

REQUIRED_IMPORTS = [
    "dotenv",
    "pydantic",
    "pydantic_settings",
    "yaml",
    "typer",
    "rich",
    "structlog",
    "pytest",
    "pandas",
    "numpy",
    "ccxt",
]


def run_install_check(config_path: Path = Path("config/default.yaml")) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    checks.append({"name": "python_version", "status": "PASS", "value": sys.version.split()[0]})
    for module in REQUIRED_IMPORTS:
        try:
            importlib.import_module(module)
        except Exception as exc:
            checks.append({"name": f"import:{module}", "status": "FAIL", "message": str(exc)})
        else:
            checks.append({"name": f"import:{module}", "status": "PASS"})
    for path in [Path("README.md"), Path("config/default.yaml"), Path("src/trading_bot")]:
        checks.append({"name": f"path:{path}", "status": "PASS" if path.exists() else "FAIL"})
    settings = load_settings(config_path)
    generate_fixtures(settings.data.cache_dir)
    checks.append({"name": "fixture_generation", "status": "PASS"})
    checks.append({"name": "env_required", "status": "PASS", "message": "no .env values required"})
    checks.append(
        {
            "name": "non_live_safety",
            "status": "PASS" if not settings.live_trading_enabled else "FAIL",
            "live_trading": False,
            "real_orders_enabled": False,
            "uses_private_api": False,
        }
    )
    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    return {
        "status": status,
        "checks": checks,
        "live_trading": False,
        "real_orders_enabled": False,
        "uses_private_api": False,
    }


def run_final_nonlive_check(
    config_path: Path = Path("config/default.yaml"),
    release_dir: Path = Path("data/processed/releases/0.1.0-rc1"),
) -> dict[str, Any]:
    settings = load_settings(config_path)
    checks: list[dict[str, Any]] = []
    for path in [
        "README.md",
        "INSTALL.md",
        "QUICKSTART.md",
        "SAFETY.md",
        "SECURITY.md",
        "docs/known_limitations.md",
        "docs/command_reference.md",
    ]:
        checks.append({"name": path, "status": "PASS" if Path(path).exists() else "FAIL"})
    checks.append(
        {
            "name": "changelog",
            "status": _contains(Path("CHANGELOG.md"), "0.1.0"),
        }
    )
    checks.append(
        {
            "name": "release_notes_limitations",
            "status": _contains(Path("RELEASE_NOTES.md"), "not approved for real-money trading"),
        }
    )
    checks.append(
        {
            "name": "feature_matrix_live_status",
            "status": _contains(Path("docs/feature_matrix.md"), "Not implemented and not approved"),
        }
    )
    try:
        verify_release_candidate(release_dir)
    except ReleaseVerificationError as exc:
        checks.append({"name": "release_verification", "status": "FAIL", "message": str(exc)})
    else:
        checks.append({"name": "release_verification", "status": "PASS"})
    audit_dir = run_safety_audit(
        settings=settings,
        include_code=True,
        include_config=True,
        include_env=False,
        include_artifacts=False,
    )
    audit_metadata = json.loads((audit_dir / "run_metadata.json").read_text(encoding="utf-8"))
    checks.append(
        {
            "name": "safety_audit",
            "status": "PASS" if audit_metadata.get("audit_result") == "PASS" else "FAIL",
        }
    )
    checks.extend(_settings_safety_checks(settings))
    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    return {"status": status, "checks": checks}


def _settings_safety_checks(settings: Settings) -> list[dict[str, Any]]:
    return [
        {
            "name": "live_trading_disabled",
            "status": "PASS" if not settings.live_trading_enabled else "FAIL",
        },
        {
            "name": "governance_real_orders_disabled",
            "status": "PASS" if not settings.governance.real_orders_allowed else "FAIL",
        },
        {
            "name": "governance_private_api_disabled",
            "status": "PASS" if not settings.governance.private_api_allowed else "FAIL",
        },
    ]


def _contains(path: Path, text: str) -> str:
    if not path.exists():
        return "FAIL"
    return "PASS" if text in path.read_text(encoding="utf-8") else "FAIL"
