from __future__ import annotations

from html import escape

from trading_bot.reporting.markdown import LIMITATIONS


def render_html_report(
    *,
    readiness: dict[str, object],
    metrics: dict[str, object],
    health: dict[str, object],
    warnings: list[str],
) -> str:
    status = escape(str(readiness["status"]))
    metric_rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in metrics.items()
    )
    gate_rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in readiness.items()
    )
    health_rows = "".join(
        f"<tr><th>{escape(str(key))}</th><td>{escape(str(value))}</td></tr>"
        for key, value in health.items()
    )
    warning_items = (
        "".join(f"<li>{escape(warning)}</li>" for warning in warnings) or "<li>None</li>"
    )
    return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Paper Trading Report</title></head>
<body>
<h1>Paper Trading Report</h1>
<p><strong>Status:</strong> <span>{status}</span></p>
<h2>Key Metrics</h2><table>{metric_rows}</table>
<h2>Readiness Gates</h2><table>{gate_rows}</table>
<h2>Health Summary</h2><table>{health_rows}</table>
<h2>Warnings</h2><ul>{warning_items}</ul>
<h2>Important Limitations</h2><p>{escape(LIMITATIONS)}</p>
</body>
</html>"""
