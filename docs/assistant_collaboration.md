# Assistant Collaboration

This repository uses GitHub `main` as the stable source of truth for all
assistants and tools. Collaboration rules are designed to prevent drift, protect
trading safety boundaries, and keep native MT5 execution paths unchanged unless
explicitly approved.

## Role Split

- ChatGPT: planning, review, architecture, risk analysis, PR review.
- Claude Chat: second-opinion reasoning, documentation review, architecture
  critique.
- Codex: implementation, tests, repository edits, command execution.
- Claude Code: implementation on feature branches only.
- Claude cowork: review and coordination only unless explicitly assigned.

## Source Of Truth

- GitHub `main` is the stable source of truth.
- All tools must pull latest `main` before starting work.
- No local-only decision counts unless it is written to repository docs, issues,
  or PRs.
- If local notes conflict with committed repo docs, treat committed repo docs as
  authoritative until a PR updates them.

## Branching

- `main` is stable and should be treated as protected.
- Implementation must happen on feature branches.
- Use branch names such as:
  - `docs/<task>`
  - `tooling/<task>`
  - `tests/<task>`
  - `research/<task>`
- Commit directly to `main` only for explicitly requested repository setup or
  documentation/process-only tasks where the user permits it.

## Pull Requests

Every code change PR must include:

- clear summary
- tests run
- risk assessment
- files changed

PRs that touch MQL5 source, Python MT5 support, settings generation, source
scanning, or audit/reporting paths must explicitly state whether strategy logic,
execution logic, account-stage gates, or protected account behavior changed.

## Prohibited Work

Do not perform any of the following without explicit approval:

- live trading enablement
- protected account execution
- Trial, Surge 2 Step, Vanguard, Challenge, Verification, or Funded expansion
- strategy parameter optimization
- strategy logic edits
- execution logic edits
- committing raw tester exports
- committing account-sensitive artifacts
- committing secrets, credentials, tokens, broker configs, account numbers,
  `.env` files, or private MT5 exports

## Current Priority

Current priority is post-Phase 14.5 Strategy Tester evidence packaging and
comparison only.

Near-term work should focus on:

- collecting exported Strategy Tester report/log folders
- packaging evidence with `scripts/collect_strategy_tester_evidence.py`
- parsing reports with `scripts/parse_strategy_tester_report.py`
- comparing runs with `scripts/compare_strategy_tester_runs.py`
- keeping all Strategy Tester conclusions research-only

Do not optimize parameters, change strategy rules, or expand live Trial
execution while this priority remains active.
