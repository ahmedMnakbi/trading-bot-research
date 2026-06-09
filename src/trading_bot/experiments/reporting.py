from __future__ import annotations

LIMITATIONS = (
    "This campaign report is not a profitability claim and is not approval for live trading. "
    "It only summarizes fixed-parameter historical tests and validation runs. Results may fail "
    "in future market conditions. Human review and paper trading remain mandatory before any "
    "real-money deployment."
)


def render_campaign_markdown(
    *,
    metadata: dict[str, object],
    matrix: list[dict[str, object]],
    results: list[dict[str, object]],
    failed: list[dict[str, object]],
    labels: dict[str, object],
    warnings: dict[str, object],
) -> str:
    return "\n".join(
        [
            "# Experiment Campaign Report",
            "",
            "## Campaign Metadata",
            str(metadata),
            "",
            "## Experiment Matrix",
            str(matrix),
            "",
            "## Completed Runs",
            str(results),
            "",
            "## Failed Runs",
            str(failed),
            "",
            "## Benchmark Summary",
            "See benchmark_summary.json.",
            "",
            "## Warning Summary",
            str(warnings),
            "",
            "## Candidate Labels",
            str(labels),
            "",
            "## Interpretation Notes",
            "Labels are conservative review signals only.",
            "",
            "## Important Limitations",
            LIMITATIONS,
        ]
    )


def render_campaign_html(
    *, labels: dict[str, object], warnings: dict[str, object], failed: list[dict[str, object]]
) -> str:
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Experiment Campaign Report</title></head>
<body>
<h1>Experiment Campaign Report</h1>
<h2>Status Summary</h2><p>Completed campaign report.</p>
<h2>Experiments</h2><p>See experiment_matrix.json.</p>
<h2>Candidate Labels</h2><pre>{labels}</pre>
<h2>Warning Summary</h2><pre>{warnings}</pre>
<h2>Failed Runs</h2><pre>{failed}</pre>
<h2>Important Limitations</h2><p>{LIMITATIONS}</p>
</body></html>"""

