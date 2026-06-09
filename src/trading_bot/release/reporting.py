from __future__ import annotations

from typing import Any

NON_LIVE_LIMITATION = (
    "This is a non-live research, backtesting, validation, campaign, and paper-trading "
    "release candidate. It is not approved for real-money trading. Live trading, real order "
    "placement, authenticated exchange clients, private account endpoints, leverage is forbidden, "
    "shorting, optimization, and machine learning remain forbidden."
)


def render_smoke_report(summary: dict[str, Any], steps: list[dict[str, Any]]) -> str:
    lines = [
        "# Non-Live Release Smoke Report",
        "",
        f"Release check: `{summary['release_check_id']}`",
        f"Status: {summary['status']}",
        "",
        "## Steps",
    ]
    lines.extend(f"- {step['name']}: {step['status']}" for step in steps)
    lines.extend(["", "## Important Limitations", NON_LIVE_LIMITATION, ""])
    return "\n".join(lines)


def render_release_report(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Non-Live Release Candidate",
            "",
            f"Version: {summary['version']}",
            f"Status: {summary['status']}",
            "",
            "## Important Limitations",
            NON_LIVE_LIMITATION,
            "",
        ]
    )
