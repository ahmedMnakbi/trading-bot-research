from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from trading_bot.config.profiles import effective_config, list_profiles
from trading_bot.config.settings import Settings

ROOT = Path(__file__).resolve().parents[1]


def test_safe_profiles_validate_successfully() -> None:
    names = {profile.name for profile in list_profiles(ROOT / "config/default.yaml")}

    assert names >= {"research", "campaign", "paper_single", "paper_portfolio", "audit"}
    for name in names:
        Settings.model_validate(effective_config(ROOT / "config/default.yaml", name))


@pytest.mark.parametrize(
    "overlay",
    [
        {"mode": "live"},
        {"live_trading_enabled": True},
        {"governance": {"real_orders_allowed": True}},
        {"governance": {"private_api_allowed": True}},
        {"risk": {"allow_leverage": True}},
        {"risk": {"allow_shorting": True}},
    ],
)
def test_unsafe_profile_overlays_fail(tmp_path: Path, overlay: dict[str, object]) -> None:
    config_dir = tmp_path / "config"
    profiles_dir = config_dir / "profiles"
    profiles_dir.mkdir(parents=True)
    default = yaml.safe_load((ROOT / "config/default.yaml").read_text(encoding="utf-8"))
    (config_dir / "default.yaml").write_text(yaml.safe_dump(default), encoding="utf-8")
    (profiles_dir / "bad.yaml").write_text(yaml.safe_dump(overlay), encoding="utf-8")

    with pytest.raises(ValueError):
        effective_config(config_dir / "default.yaml", "bad")
