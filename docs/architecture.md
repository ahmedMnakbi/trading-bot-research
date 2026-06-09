# Architecture

## Current Scope

Task 1 provides:

- Typed configuration loading and validation
- A CLI entry point
- Structured logging with secret redaction
- Risk limit validation
- An armed-by-default kill switch
- Tests for safety defaults

## Explicit Non-Goals

- No live exchange trading
- No real orders
- No strategy optimization
- No broker or exchange execution adapter

## Package Layout

- `trading_bot.config`: settings models and YAML loading
- `trading_bot.risk`: kill switch and risk limit helpers
- `trading_bot.utils`: logging configuration
- `trading_bot.main`: CLI commands

