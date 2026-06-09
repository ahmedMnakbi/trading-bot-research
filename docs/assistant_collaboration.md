# Assistant Collaboration

This repository uses GitHub `main` as the stable source of truth for all
assistants and tools. Collaboration rules are designed to prevent drift, protect
trading safety boundaries, and keep native MT5 execution paths unchanged unless
explicitly approved.

## Role Split

### ChatGPT

- Primary planning lead.
- Strategy research partner.
- Spec writer.
- Phase planner.
- PR review support.
- Does not touch code or run commands.

### Claude Chat

- Second-opinion reviewer.
- Safety challenger.
- Architecture critique.
- Reviews specs before implementation.
- Challenges prop-firm risk, signal-contract problems, unsafe assumptions, and
  phase-gate violations.
- Does not write code or make sequential implementation decisions.

### Codex

- Python support tooling.
- Tests.
- Command execution.
- Strategy Tester evidence collection and comparison.
- Source scans, pytest, ruff, and compile checks where available.
- Does not make architecture or strategy-concept decisions.

### Claude Code

- MQL5 source implementation on feature branches only.
- Implements only from approved, committed specs.
- Must read `AGENTS.md`, `PROJECT_HANDOFF.md`, and relevant docs before coding.
- Must not touch execution or protected-account modules without explicit written
  approval.

### Claude Cowork

- Coordination and task tracking.
- Keeps `PROJECT_HANDOFF.md` current at phase boundaries.
- Confirms what is approved, pending, blocked, or rejected.
- Prevents agents from working from stale context.

## Core Workflow

ChatGPT proposes. Claude Chat challenges. User approves. Codex or Claude Code
implements only after approval. Claude Cowork updates handoff state.

## Operating Rules

### Rule 1

Nothing enters implementation without an approved, committed spec.

### Rule 2

`PROJECT_HANDOFF.md` must be updated before each major agent switch or phase
transition.

### Rule 3

Planning agents never unblock themselves. The user is the decision-maker at
every phase gate.

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

Current priority is fast strategy iteration with structured manual MT5 Strategy
Tester summaries. Full Strategy Tester evidence packaging remains available and
recommended for serious candidate strategies, but it is no longer required for
every exploratory run.

Near-term work should focus on:

- drafting approved committed specs before implementation
- running local MT5 Strategy Tester research
- reporting results with `docs/manual_backtest_result_template.md`
- comparing structured manual results before deciding whether to reject, revise,
  expand testing, or promote a strategy to Trial-sandbox candidate review
- optionally packaging serious candidate results with
  `scripts/collect_strategy_tester_evidence.py`,
  `scripts/parse_strategy_tester_report.py`, and
  `scripts/compare_strategy_tester_runs.py`
- keeping all Strategy Tester conclusions research-only

Do not optimize parameters, change strategy rules, or expand live Trial
execution while this priority remains active.

## Fast Manual Testing Mode

Manual MT5 Strategy Tester results are allowed for faster strategy iteration.
The user may report backtest metrics directly instead of packaging raw tester
exports for every run.

Strategy decisions should still be based on structured reported metrics. Use
`docs/manual_backtest_result_template.md` so runs remain comparable and do not
get lost in chat context. Manual reports are research notes, not formal audit
evidence, profitability proof, or approval for Trial, Surge 2 Step, Vanguard,
Challenge, Verification, Funded, or live-money execution.

Free Trial or demo testing may be considered only after a strategy has an
approved committed spec, a clean source scan, a successful compile, and at least
basic manual tester results. Real-money and protected-account execution remain
blocked unless explicitly approved in a later phase.

## Strategy-From-Scratch Workflow

Use this flow for any new strategy concept:

1. Raw user idea.
2. ChatGPT drafts research concept/spec.
3. Claude Chat critiques risks and architecture.
4. User approves or revises.
5. ChatGPT finalizes committed spec.
6. Claude Cowork updates `PROJECT_HANDOFF.md`.
7. Claude Code implements MQL5 module on a feature branch.
8. Codex writes and runs tests, source scan, compile checks, and evidence
   tooling.
9. Claude Chat reviews branch and evidence.
10. User approves merge.
11. Claude Cowork closes phase in `PROJECT_HANDOFF.md`.
