from __future__ import annotations

from trading_bot.config.settings import RiskSettings


def validate_risk_limits(risk: RiskSettings) -> RiskSettings:
    """Return validated risk settings without creating any trading side effects."""
    return RiskSettings.model_validate(risk.model_dump())

