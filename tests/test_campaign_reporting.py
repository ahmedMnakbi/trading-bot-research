from __future__ import annotations

from trading_bot.experiments.reporting import LIMITATIONS, render_campaign_markdown


def test_campaign_report_includes_required_limitations_text() -> None:
    report = render_campaign_markdown(
        metadata={},
        matrix=[],
        results=[],
        failed=[],
        labels={},
        warnings={},
    )
    assert LIMITATIONS in report
