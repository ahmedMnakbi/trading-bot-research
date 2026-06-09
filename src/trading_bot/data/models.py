from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OhlcvCandle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

    @field_validator("timestamp")
    @classmethod
    def require_utc_timestamp(cls, timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        utc_timestamp = timestamp.astimezone(UTC)
        if utc_timestamp.utcoffset() != timestamp.utcoffset():
            raise ValueError("timestamp must be UTC")
        return utc_timestamp

    @model_validator(mode="after")
    def validate_ohlc_bounds(self) -> OhlcvCandle:
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must be greater than or equal to open, low, and close")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be less than or equal to open, high, and close")
        return self

