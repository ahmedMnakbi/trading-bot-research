from __future__ import annotations

from trading_bot.mt5.models import Mt5AssetClass

FOREX_CODES = {
    "AUD",
    "CAD",
    "CHF",
    "EUR",
    "GBP",
    "JPY",
    "NZD",
    "USD",
}
GOLD_ALIASES = {"XAU", "GOLD"}
CRYPTO_ALIASES = {"BTC", "ETH", "XBT", "LTC", "XRP", "SOL", "DOGE", "ADA"}
INDEX_ALIASES = {
    "US30",
    "DJ30",
    "NAS100",
    "USTEC",
    "US100",
    "SPX500",
    "US500",
    "GER40",
    "DAX",
    "UK100",
    "JP225",
}
COMMODITY_ALIASES = {"XAG", "SILVER", "OIL", "WTI", "BRENT", "NGAS", "COPPER"}


def categorize_symbol(name: str, *, path: str | None = None) -> Mt5AssetClass:
    upper_name = _normalize(name)
    upper_path = _normalize(path or "")
    combined = f"{upper_name} {upper_path}"
    if any(alias in combined for alias in GOLD_ALIASES):
        return Mt5AssetClass.GOLD
    if any(alias in combined for alias in CRYPTO_ALIASES):
        return Mt5AssetClass.CRYPTO
    if any(alias in combined for alias in INDEX_ALIASES):
        return Mt5AssetClass.INDEX
    if any(alias in combined for alias in COMMODITY_ALIASES):
        return Mt5AssetClass.COMMODITY
    if _looks_like_forex(upper_name):
        return Mt5AssetClass.FOREX
    if "FOREX" in upper_path or "FX" in upper_path:
        return Mt5AssetClass.FOREX
    if "INDEX" in upper_path or "INDICES" in upper_path:
        return Mt5AssetClass.INDEX
    if "CRYPTO" in upper_path:
        return Mt5AssetClass.CRYPTO
    if "COMMOD" in upper_path or "METAL" in upper_path or "ENERGY" in upper_path:
        return Mt5AssetClass.COMMODITY
    return Mt5AssetClass.UNKNOWN


def _looks_like_forex(value: str) -> bool:
    compact = "".join(character for character in value if character.isalpha())
    if len(compact) < 6:
        return False
    base = compact[:3]
    quote = compact[3:6]
    return base in FOREX_CODES and quote in FOREX_CODES


def _normalize(value: str) -> str:
    return value.upper().replace("/", "").replace("-", "").replace("_", "")

