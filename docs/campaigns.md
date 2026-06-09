# Campaigns

Run a campaign with:

```bash
python -m trading_bot run-campaign --config config/default.yaml --exchange kraken
```

Artifacts are written under `data/processed/campaigns/{campaign_run_id}/` and include the matrix, results, warnings, labels, failed runs, reports, metadata, and an artifact manifest.

Candidate labels are conservative:

- `REJECTED`
- `NEEDS_MORE_DATA`
- `PAPER_TRADING_CANDIDATE`

`PAPER_TRADING_CANDIDATE` only means eligible for further paper-trading review. It is not a profitability claim and not live-trading approval.

Campaign reports should be interpreted as fixed-parameter historical summaries. Human review and paper trading remain mandatory before any real-money deployment.

