"""Curated NIFTY-50 symbol metadata (name + sector).

Owner: Chirag (seed uses this) / shared.

Sector data is not reliably available offline from ``nsepython`` (no sector field
in its symbol list), so this is a static, deterministic map. ISIN stays ``None``;
enrich later if a source for it becomes available.
"""

from __future__ import annotations

from app.schemas import SymbolInfo

_META: dict[str, tuple[str, str]] = {
    "ADANIENT": ("Adani Enterprises", "Diversified"),
    "ADANIPORTS": ("Adani Ports and SEZ", "Infrastructure"),
    "APOLLOHOSP": ("Apollo Hospitals", "Healthcare"),
    "ASIANPAINT": ("Asian Paints", "Consumer"),
    "AXISBANK": ("Axis Bank", "Banking"),
    "BAJAJ-AUTO": ("Bajaj Auto", "Automobile"),
    "BAJAJFINANCE": ("Bajaj Finance", "Financial Services"),
    "BAJAJFINSV": ("Bajaj Finserv", "Financial Services"),
    "BEL": ("Bharat Electronics", "Defence"),
    "BHARTIARTL": ("Bharti Airtel", "Telecom"),
    "CIPLA": ("Cipla", "Pharmaceuticals"),
    "COALINDIA": ("Coal India", "Mining"),
    "DRREDDY": ("Dr. Reddy's Laboratories", "Pharmaceuticals"),
    "EICHERMOT": ("Eicher Motors", "Automobile"),
    "ETERNAL": ("Eternal", "Media"),
    "GRASIM": ("Grasim Industries", "Cement"),
    "HCLTECH": ("HCL Technologies", "IT Services"),
    "HDFCBANK": ("HDFC Bank", "Banking"),
    "HDFCLIFE": ("HDFC Life Insurance", "Insurance"),
    "HEROMOTOCO": ("Hero MotoCorp", "Automobile"),
    "HINDALCO": ("Hindalco Industries", "Metals"),
    "HINDUNILVR": ("Hindustan Unilever", "FMCG"),
    "ICICIBANK": ("ICICI Bank", "Banking"),
    "INDUSINDBK": ("IndusInd Bank", "Banking"),
    "INFY": ("Infosys", "IT Services"),
    "ITC": ("ITC", "FMCG"),
    "JSWSTEEL": ("JSW Steel", "Metals"),
    "KOTAKBANK": ("Kotak Mahindra Bank", "Banking"),
    "LT": ("Larsen & Toubro", "Infrastructure"),
    "M&M": ("Mahindra & Mahindra", "Automobile"),
    "MARUTI": ("Maruti Suzuki India", "Automobile"),
    "MAXHEALTH": ("Max Healthcare Institute", "Healthcare"),
    "NESTLEIND": ("Nestle India", "FMCG"),
    "NTPC": ("NTPC", "Power"),
    "ONGC": ("Oil & Natural Gas Corporation", "Oil & Gas"),
    "POWERGRID": ("Power Grid Corporation", "Power"),
    "RELIANCE": ("Reliance Industries", "Energy"),
    "SBILIFE": ("SBI Life Insurance", "Insurance"),
    "SBIN": ("State Bank of India", "Banking"),
    "SHRIRAMFIN": ("Shriram Finance", "Financial Services"),
    "SUNPHARMA": ("Sun Pharmaceutical", "Pharmaceuticals"),
    "TATACONSUM": ("Tata Consumer Products", "FMCG"),
    "TATAMOTORS": ("Tata Motors", "Automobile"),
    "TATASTEEL": ("Tata Steel", "Metals"),
    "TCS": ("Tata Consultancy Services", "IT Services"),
    "TECHM": ("Tech Mahindra", "IT Services"),
    "TITAN": ("Titan Company", "Consumer"),
    "TRENT": ("Trent", "Retail"),
    "ULTRACEMCO": ("UltraTech Cement", "Cement"),
    "WIPRO": ("Wipro", "IT Services"),
}

INDEX_SYMBOL = "^NSEI"


def symbol_info(symbol: str) -> SymbolInfo:
    """Return metadata for one symbol (``.NS`` constituent or ``^NSEI``)."""
    if symbol == INDEX_SYMBOL:
        return SymbolInfo(
            symbol=symbol,
            name="NIFTY 50",
            exchange="NSE",
            index_member=False,
            isin=None,
            sector="Index",
        )
    ticker = symbol.removesuffix(".NS")
    name, sector = _META.get(ticker, (ticker, None))
    return SymbolInfo(
        symbol=symbol,
        name=name,
        exchange="NSE",
        index_member=True,
        isin=None,
        sector=sector,
    )
