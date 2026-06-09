# MetaEditor Compile Workflow

MetaEditor tooling is used only to compile the project-local native EA source and collect diagnostics. It does not enable trading, use credentials, open live trading, or approve prop challenge use.

## Detect MetaEditor

Use:

```powershell
python scripts/check_metaeditor.py
python scripts/check_metaeditor.py --metaeditor-path "C:\Program Files\MetaTrader 5\metaeditor64.exe"
```

The script checks common Windows MetaEditor and MT5 terminal paths. It does not launch MT5 login, use credentials, modify terminal settings, or enable Algo Trading.

If MetaEditor is missing, the result is `SKIPPED` with manual installation instructions. If MetaEditor exists but the terminal is missing, the result is `WARN`.

## Compile Future EA Source

Use:

```powershell
python scripts/compile_mql5_ea.py
```

Before Phase 4, the expected EA source did not exist, so the script reported `SKIPPED`, not `FAIL`. In Phase 5 the monitor-only source exists, so MetaEditor compile should either produce `PASS` or actionable compile diagnostics. It writes logs under `data/processed/mql5_compile/`.

The wrapper compiles only `mql5/Experts/UpcomersNYSessionPropBot/UpcomersNYSessionPropBot.mq5`. It must not require prop credentials, open live trading, or compile arbitrary community EA code.

If project-relative includes do not resolve on a local terminal, copy the repo `mql5/Include/UpcomersNYSessionPropBot` folder into the terminal data folder's `MQL5/Include/` directory and copy the EA file into `MQL5/Experts/UpcomersNYSessionPropBot/`, then compile manually in MetaEditor. Manual compile is still monitor-only and must not involve account login or trading permissions.

A compile PASS means syntax passed. It is not approval for Surge 2 Step, Vanguard, Challenge, Verification, Funded, or any live use. Source scan PASS, compile PASS, exact account-program rules, trial evidence, final audit package ID, and explicit human approval metadata are all still required before any later protected preset discussion.
