from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from trading_bot.mt5.transformation import load_mt5_transformation_config


def _write_config(tmp_path: Path, overrides: dict[str, object]) -> Path:
    base = yaml.safe_load(Path("config/mt5_transformation.yaml").read_text(encoding="utf-8"))
    _deep_update(base, overrides)
    path = tmp_path / "mt5_transformation.yaml"
    path.write_text(yaml.safe_dump(base), encoding="utf-8")
    return path


def _deep_update(target: dict[str, object], overrides: dict[str, object]) -> None:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)  # type: ignore[arg-type]
        else:
            target[key] = value


def test_mt5_transformation_defaults_are_safe() -> None:
    config = load_mt5_transformation_config("config/mt5_transformation.yaml")

    assert config.live_trading_enabled is False
    assert config.mt5.enabled is False
    assert config.mt5.mode == "readonly"
    serialized = config.model_dump(by_alias=True)
    assert serialized["mt5"]["allow_order_send"] is False
    assert serialized["mt5"]["allow_order_check"] is False
    assert serialized["mt5"]["allow_account_info"] is False
    assert config.mt5.allow_positions is False
    assert config.mt5.allow_balance_fetching is False
    assert config.mt5.allow_live_account is False
    assert config.mt5.allow_demo_account is False
    assert config.ny_session.enabled is False
    assert config.ny_session.timezone == "America/New_York"
    assert config.execution.enabled is False
    assert config.execution.demo_only is True
    assert config.execution.live_allowed is False
    assert config.prop_firm.execution_path == "native_mql5_ea"
    assert config.prop_firm.python_mt5_execution_quarantined is True
    assert config.prop_firm.account_programs_supported == [
        "TrialRiskFree",
        "Vanguard",
        "Surge2Step",
        "Custom",
    ]
    assert config.prop_firm.trial_required_before_challenge is True
    assert config.prop_firm.protected_account_programs_blocked is True
    assert config.prop_firm.surge_2_step_rules_verified is False
    assert config.prop_firm.vanguard_rules_verified is False
    assert config.prop_firm.prop_day_reset_timezone == "UNCONFIRMED_CONSERVATIVE"
    assert config.prop_firm.prop_day_reset_timezone_confirmed is False
    assert config.prop_firm.dynamic_risk_shield_verified is False
    assert config.prop_firm.challenge_presets_enabled is False
    assert config.prop_firm.required_challenge_preset_evidence.complete() is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"live_trading_enabled": True},
        {"mt5": {"allow_order_send": True}},
        {"mt5": {"allow_order_check": True}},
        {"mt5": {"allow_account_info": True}},
        {"mt5": {"allow_positions": True}},
        {"mt5": {"allow_balance_fetching": True}},
        {"mt5": {"allow_live_account": True}},
        {"execution": {"enabled": True}},
        {"execution": {"demo_only": False}},
        {"execution": {"live_allowed": True}},
        {"prop_firm": {"python_mt5_execution_quarantined": False}},
        {"prop_firm": {"account_programs_supported": ["TrialRiskFree", "Vanguard"]}},
        {"prop_firm": {"trial_required_before_challenge": False}},
        {"prop_firm": {"protected_account_programs_blocked": False}},
        {"prop_firm": {"surge_2_step_rules_verified": True}},
        {"prop_firm": {"vanguard_rules_verified": True}},
        {"prop_firm": {"challenge_presets_enabled": True}},
    ],
)
def test_mt5_transformation_rejects_unsafe_gates(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    path = _write_config(tmp_path, overrides)

    with pytest.raises(ValidationError):
        load_mt5_transformation_config(path)


def test_challenge_presets_require_complete_evidence(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path,
        {
            "prop_firm": {
                "challenge_presets_enabled": True,
                "prop_day_reset_timezone_confirmed": True,
                "dynamic_risk_shield_verified": True,
                "required_challenge_preset_evidence": {
                    "trial_evidence": True,
                    "source_scan_pass": True,
                    "compile_pass": True,
                    "audit_package_id": "audit-package-1",
                    "explicit_human_approval_metadata": "approved-by-user-2026-05-31",
                },
            }
        },
    )

    config = load_mt5_transformation_config(path)

    assert config.prop_firm.challenge_presets_enabled is True
