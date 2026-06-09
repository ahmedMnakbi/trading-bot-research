"""Support-only tooling for the native MQL5 EA.

This package provides static scanning, settings generation, log parsing, and
compliance reporting. It is not an MT5 execution layer.
"""

from trading_bot.mql5.compliance_report import export_prop_compliance_report
from trading_bot.mql5.log_parser import parse_ea_logs
from trading_bot.mql5.settings import build_settings, generate_settings_artifacts
from trading_bot.mql5.source_scan import scan_mql5_source_tree

__all__ = [
    "build_settings",
    "export_prop_compliance_report",
    "generate_settings_artifacts",
    "parse_ea_logs",
    "scan_mql5_source_tree",
]
