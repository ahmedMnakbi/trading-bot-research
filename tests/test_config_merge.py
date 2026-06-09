from __future__ import annotations

from trading_bot.config.merge import deep_merge


def test_config_merge_preserves_safe_defaults() -> None:
    merged = deep_merge(
        {"mode": "paper", "risk": {"allow_leverage": False, "max_open_positions": 3}},
        {"risk": {"max_open_positions": 1}},
    )

    assert merged["mode"] == "paper"
    assert merged["risk"]["allow_leverage"] is False
    assert merged["risk"]["max_open_positions"] == 1
