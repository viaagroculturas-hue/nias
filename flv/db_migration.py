"""Runtime schema compatibility migrations for NIAS SQLite.

These migrations are intentionally conservative: they only add missing columns
used by the current APIs, never delete or rewrite user data.
"""
from __future__ import annotations

import sqlite3
from typing import Dict

# ─── DDL: tabela nias_regions (polos sul-americanos) ──────────────────────────
_NIAS_REGIONS_DDL = """
CREATE TABLE IF NOT EXISTS nias_regions (
  id                  TEXT PRIMARY KEY,
  scope               TEXT DEFAULT 'south_america',
  country             TEXT NOT NULL,
  country_code        TEXT NOT NULL,
  region              TEXT NOT NULL,
  state_or_department TEXT,
  city                TEXT,
  lat                 REAL NOT NULL,
  lon                 REAL NOT NULL,
  products            TEXT,
  importance          TEXT,
  notes               TEXT,
  source              TEXT DEFAULT 'NIAS',
  active              INTEGER DEFAULT 1,
  created_at          TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
)
"""

# table -> {column: SQL type/default clause}
_REQUIRED_COLUMNS: Dict[str, Dict[str, str]] = {
    "flv_ceasa_prices": {
        "is_synthetic": "INTEGER DEFAULT 0",
        "data_quality": "TEXT DEFAULT 'official_or_observed'",
    },
    "flv_climate": {
        "is_synthetic":  "INTEGER DEFAULT 0",
        "data_quality":  "TEXT DEFAULT 'official_or_observed'",
        "scope":         "TEXT DEFAULT 'brazil'",
        "country_code":  "TEXT",
        "region_id":     "TEXT",
        "region_name":   "TEXT",
        "lat":           "REAL",
        "lon":           "REAL",
    },
    "flv_ndvi": {
        "is_synthetic": "INTEGER DEFAULT 0",
        "data_quality": "TEXT DEFAULT 'official_or_observed'",
    },
    "flv_production": {
        "is_synthetic": "INTEGER DEFAULT 0",
        "data_quality": "TEXT DEFAULT 'official_or_observed'",
    },
    "flv_macro_indicators": {
        "is_synthetic": "INTEGER DEFAULT 0",
        "data_quality": "TEXT DEFAULT 'official_or_observed'",
    },
    "flv_global_climate": {
        "is_synthetic": "INTEGER DEFAULT 0",
        "data_quality": "TEXT DEFAULT 'official_or_observed'",
    },
    "flv_news_events": {
        "is_synthetic": "INTEGER DEFAULT 0",
        "data_quality": "TEXT DEFAULT 'official_or_observed'",
    },
}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (table,)
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def ensure_runtime_schema(conn: sqlite3.Connection) -> None:
    """Add missing compatibility columns needed by live APIs."""
    changed = False

    # Criar tabela nias_regions se não existir
    conn.execute(_NIAS_REGIONS_DDL)
    changed = True  # CREATE IF NOT EXISTS é idempotente

    for table, cols in _REQUIRED_COLUMNS.items():
        if not _table_exists(conn, table):
            continue
        existing = _columns(conn, table)
        for col, ddl in cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                changed = True
    if changed:
        conn.commit()


def ensure_path_schema(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        ensure_runtime_schema(conn)
    finally:
        conn.close()
