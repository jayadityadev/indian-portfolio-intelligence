"""Symbol universe.

Owner: Jayaditya (interface) / Chirag (Postgres ``symbols`` seed uses this).

Contract:
    nifty50_symbols() -> list[str]   # "RELIANCE.NS", ..., plus index "^NSEI"
    nifty50_index() -> str           # "^NSEI"
"""

from __future__ import annotations


def nifty50_symbols() -> list[str]:
    """Return current NIFTY-50 constituent symbols in yfinance format (.NS)."""
    symbols = [
        "ADANIENT",
        "ADANIPORTS",
        "APOLLOHOSP",
        "ASIANPAINT",
        "AXISBANK",
        "BAJAJ-AUTO",
        "BAJAJFINANCE",
        "BAJAJFINSV",
        "BEL",
        "BHARTIARTL",
        "CIPLA",
        "COALINDIA",
        "DRREDDY",
        "EICHERMOT",
        "ETERNAL",
        "GRASIM",
        "HCLTECH",
        "HDFCBANK",
        "HDFCLIFE",
        "HEROMOTOCO",
        "HINDALCO",
        "HINDUNILVR",
        "ICICIBANK",
        "INDUSINDBK",
        "INFY",
        "ITC",
        "JSWSTEEL",
        "KOTAKBANK",
        "LT",
        "M&M",
        "MARUTI",
        "MAXHEALTH",
        "NESTLEIND",
        "NTPC",
        "ONGC",
        "POWERGRID",
        "RELIANCE",
        "SBILIFE",
        "SBIN",
        "SHRIRAMFIN",
        "SUNPHARMA",
        "TATACONSUM",
        "TATAMOTORS",
        "TATASTEEL",
        "TCS",
        "TECHM",
        "TITAN",
        "TRENT",
        "ULTRACEMCO",
        "WIPRO",
    ]
    return [f"{symbol}.NS" for symbol in symbols]


def nifty50_index() -> str:
    return "^NSEI"
