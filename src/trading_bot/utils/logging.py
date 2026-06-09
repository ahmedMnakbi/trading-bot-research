from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from typing import Any

import structlog

SECRET_KEYS = {"api_key", "api_secret", "secret", "password", "token", "exchange_api_key"}
REDACTED = "[REDACTED]"


def _is_secret_key(key: str) -> bool:
    normalized = key.lower()
    return any(secret_key in normalized for secret_key in SECRET_KEYS)


def redact_secrets(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: REDACTED if _is_secret_key(str(key)) else redact_secrets(nested)
            for key, nested in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    return value


def _redact_processor(
    _logger: logging.Logger, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    return redact_secrets(event_dict)


def configure_logging(*, mode: str, component: str = "app") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp", utc=True),
            structlog.processors.add_log_level,
            _redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(mode=mode, component=component)


def get_logger(*, component: str, mode: str | None = None) -> structlog.stdlib.BoundLogger:
    logger = structlog.get_logger().bind(component=component)
    if mode is not None:
        logger = logger.bind(mode=mode)
    return logger

