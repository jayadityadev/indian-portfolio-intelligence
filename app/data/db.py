"""Postgres access for the symbols metadata table.

Owner: Chirag (seed uses this) / shared.

The ``symbols`` table is a metadata store (name, sector, exchange, index
membership, ISIN). It is deliberately separate from the parquet time-series
cache, which remains the source of truth for OHLCV data.
"""

from __future__ import annotations

import psycopg

from app.config import settings
from app.schemas import SymbolInfo

_CREATE_SYMBOLS_SQL = """
CREATE TABLE IF NOT EXISTS symbols (
    symbol       TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    exchange     TEXT NOT NULL,
    index_member BOOLEAN NOT NULL DEFAULT FALSE,
    isin         TEXT,
    sector       TEXT
)
"""

_UPSERT_SYMBOLS_SQL = """
INSERT INTO symbols (symbol, name, exchange, index_member, isin, sector)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (symbol) DO UPDATE SET
    name = EXCLUDED.name,
    exchange = EXCLUDED.exchange,
    index_member = EXCLUDED.index_member,
    isin = EXCLUDED.isin,
    sector = EXCLUDED.sector
"""


def create_schema() -> None:
    with psycopg.connect(settings.postgres_dsn) as conn:
        conn.execute(_CREATE_SYMBOLS_SQL)


def upsert_symbols(rows: list[SymbolInfo]) -> int:
    """Insert or update symbol metadata; returns the number of rows written."""
    with psycopg.connect(settings.postgres_dsn) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    _UPSERT_SYMBOLS_SQL,
                    (
                        row.symbol,
                        row.name,
                        row.exchange,
                        row.index_member,
                        row.isin,
                        row.sector,
                    ),
                )
            conn.commit()
    return len(rows)
