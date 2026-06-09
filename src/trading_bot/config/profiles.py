from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from trading_bot.config.merge import deep_merge
from trading_bot.config.settings import Settings, load_yaml

FORBIDDEN_PROFILE_VALUES = [
    (("mode",), "live"),
    (("live_trading_enabled",), True),
    (("governance", "live_trading_allowed"), True),
    (("governance", "real_orders_allowed"), True),
    (("governance", "private_api_allowed"), True),
    (("risk", "allow_leverage"), True),
    (("risk", "allow_shorting"), True),
]


@dataclass(frozen=True)
class ProfileInfo:
    name: str
    path: Path
    description: str | None
    intended_use: str | None
    safety_valid: bool
    warnings: list[str]


def profile_dir(config_path: Path) -> Path:
    return config_path.parent / "profiles"


def load_profile(
    profile_name: str,
    config_path: Path = Path("config/default.yaml"),
) -> dict[str, Any]:
    path = profile_dir(config_path) / f"{profile_name}.yaml"
    if not path.exists():
        raise ValueError(f"profile not found: {profile_name}")
    return load_yaml(path)


def list_profiles(config_path: Path = Path("config/default.yaml")) -> list[ProfileInfo]:
    profiles = []
    for path in sorted(profile_dir(config_path).glob("*.yaml")):
        raw = load_yaml(path)
        warnings = validate_profile_overlay(raw)
        profiles.append(
            ProfileInfo(
                name=path.stem,
                path=path,
                description=_meta(raw).get("description"),
                intended_use=_meta(raw).get("intended_use"),
                safety_valid=not warnings,
                warnings=warnings,
            )
        )
    return profiles


def effective_config(config_path: Path, profile_name: str | None = None) -> dict[str, Any]:
    base = load_yaml(config_path)
    if profile_name is None:
        return base
    overlay = load_profile(profile_name, config_path)
    warnings = validate_profile_overlay(overlay)
    if warnings:
        raise ValueError("; ".join(warnings))
    overlay = {key: value for key, value in overlay.items() if key != "profile"}
    return deep_merge(base, overlay)


def settings_from_profile(config_path: Path, profile_name: str | None = None) -> Settings:
    return Settings.model_validate(effective_config(config_path, profile_name))


def validate_profile_overlay(overlay: dict[str, Any]) -> list[str]:
    warnings = []
    for path, forbidden in FORBIDDEN_PROFILE_VALUES:
        present, value = _get_path(overlay, path)
        if present and value == forbidden:
            warnings.append(f"profile may not set {'.'.join(path)}={forbidden}")
    return warnings


def redacted_config(data: dict[str, Any]) -> dict[str, Any]:
    def redact(value: Any, key: str = "") -> Any:
        if isinstance(value, dict):
            return {nested_key: redact(nested, nested_key) for nested_key, nested in value.items()}
        markers = ("se" + "cret", "pass" + "word", "token", "api_key")
        if any(marker in key.lower() for marker in markers):
            return "<redacted>"
        return value

    return redact(data)


def dump_effective_config(data: dict[str, Any]) -> str:
    return yaml.safe_dump(redacted_config(data), sort_keys=False)


def _meta(raw: dict[str, Any]) -> dict[str, str]:
    meta = raw.get("profile", {})
    return meta if isinstance(meta, dict) else {}


def _get_path(data: dict[str, Any], path: tuple[str, ...]) -> tuple[bool, Any]:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current
