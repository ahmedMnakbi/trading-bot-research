from pathlib import Path

REQUIRED_STATEMENT = (
    "The final Upcomers prop-firm execution path is a native MQL5 Expert Advisor. "
    "Python-controlled MT5 execution is quarantined as legacy non-prop-compatible code"
)

REQUIRED_DOCS = [
    Path("docs/mt5_master_plan.md"),
    Path("docs/mt5_transformation_roadmap.md"),
    Path("docs/mt5_architecture.md"),
    Path("docs/mt5_safety_model.md"),
    Path("docs/mt5_strategy_research_plan.md"),
    Path("docs/mt5_execution_gates.md"),
    Path("docs/mt5_final_audit_checklist.md"),
    Path("docs/mt5_current_state_freeze.md"),
    Path("docs/upcomers_native_ea_direction_lock.md"),
]


def test_mt5_plan_docs_exist_and_state_no_live_trading() -> None:
    for path in REQUIRED_DOCS:
        assert path.exists(), f"missing {path}"
        text = path.read_text(encoding="utf-8")
        assert REQUIRED_STATEMENT in text
        assert "vanguard" in text.lower() or (
            "native MQL5 Expert Advisor" in text
        )


def test_mt5_roadmap_contains_required_phases() -> None:
    text = Path("docs/mt5_transformation_roadmap.md").read_text(encoding="utf-8")
    required_phases = [
        "Phase 0 - Current State Freeze",
        "Phase 1 - MT5 Read-Only Foundation",
        "Phase 2 - MT5 Historical Data Ingestion",
        "Phase 3 - NY Session Strategy Engine",
        "Phase 4 - MT5 Backtesting and Validation",
        "Phase 5 - Strategy Campaigns On MT5 Data",
        "Phase 6 - Native EA Monitor-Only Skeleton",
        "Phase 7 - Native EA Risk And Compliance Guards",
        "Phase 8 - Trial MT5 Platform Observation",
        "Phase 9 - Final Audit Agent Review",
        "Phase 10 - Prop Challenge Readiness Design",
        "Phase 11 - Explicitly Approved Prop Deployment Work",
    ]
    for phase in required_phases:
        assert phase in text


def test_mt5_docs_define_dst_aware_new_york_sessions() -> None:
    text = Path("docs/mt5_master_plan.md").read_text(encoding="utf-8")

    assert "08:00-17:00 America/New_York" in text
    assert "08:00-12:00 America/New_York" in text
    assert "09:30-16:00 America/New_York" in text
    assert "UTC-05:00" in text
    assert "UTC-04:00" in text
    assert "Broker/server timestamps" in text


def test_feature_matrix_marks_mt5_live_features_forbidden() -> None:
    text = Path("docs/feature_matrix.md").read_text(encoding="utf-8")

    required_rows = [
        "| MT5 live trading | Not implemented / Forbidden |",
        "| MT5 order placement | Not implemented / Forbidden |",
        "| MT5 account reads | Not implemented / Forbidden |",
        "| MT5 position reads | Not implemented / Forbidden |",
        "| MT5 balance fetching | Not implemented / Forbidden |",
        "| Python MT5 execution | Quarantined / Non-prop-compatible |",
        "| Native MQL5 EA source | Monitor-only source exists / Not execution-ready |",
        "| Native MQL5 EA execution | Not execution-ready / Approval blocked |",
    ]
    for row in required_rows:
        assert row in text


def test_known_limitations_mentions_mt5_broker_specific_risks() -> None:
    text = Path("docs/known_limitations.md").read_text(encoding="utf-8")

    for required in [
        "broker-specific symbols",
        "spread widening",
        "slippage",
        "stop-level restrictions",
        "minimum lot and lot step",
        "news volatility",
        "broker time zones",
        "demo/live differences",
        "Daily loss reset timezone",
        "Exact Dynamic Risk Shield calculation",
    ]:
        assert required in text


def test_direction_lock_requires_challenge_preset_evidence() -> None:
    text = Path("docs/upcomers_native_ea_direction_lock.md").read_text(encoding="utf-8")

    for required in [
        "Trial Risk-Free account is the first MT5 platform testing environment",
        "source scan PASS",
        "compile PASS",
        "audit package ID",
        "explicit human approval metadata",
        "PropDayResetTimezone",
        "Dynamic Risk Shield",
    ]:
        assert required in text


def test_before_trial_observation_todo_lists_phase8_blockers() -> None:
    text = Path("docs/before_trial_observation_todo.md").read_text(encoding="utf-8")

    for required in [
        "DST-aware broker server time to New York conversion",
        "closed-bar-only strategy evaluation",
        "opening range breakout minutes-to-bars handling",
        "OnTick/OnTimer throttling",
        "spread gate",
        "trade/message counter semantics",
        "Surge 2 Step rules",
        "Vanguard rules",
    ]:
        assert required in text
