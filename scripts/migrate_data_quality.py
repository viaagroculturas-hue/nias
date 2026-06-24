"""One-shot migration for FLV data quality fixes.

- Adds is_synthetic/data_quality columns to collected-data tables.
- Normalizes legacy CEASA/CONAB date strings to ISO YYYY-MM-DD.
- Marks proxy/synthetic/reference rows explicitly.
- Removes empty global climate rows and out-of-range macro indicators.
"""
from __future__ import annotations

import os
import sqlite3
from flv.data_quality import normalize_date, quality_for_source, valid_percent

DB_CANDIDATES = [
    os.path.join(os.path.dirname(__file__), "nia_flv.db"),
    os.path.join(os.path.dirname(__file__), "flv", "nia_flv.db"),
    os.path.join(os.path.dirname(__file__), "data", "ceasa", "ceasa.db"),
]

TABLES = [
    "flv_ceasa_prices", "flv_climate", "flv_ndvi", "flv_production",
    "flv_macro_indicators", "flv_news_events", "flv_global_climate",
]


def _has_table(conn, table):
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def _cols(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def _add_quality_columns(conn):
    for table in TABLES:
        if not _has_table(conn, table):
            continue
        cols = _cols(conn, table)
        if "is_synthetic" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN is_synthetic INTEGER DEFAULT 0")
        if "data_quality" not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN data_quality TEXT DEFAULT 'official_or_observed'")


def _normalize_prices(conn):
    if not _has_table(conn, "flv_ceasa_prices"):
        return 0
    changed = 0
    rows = conn.execute("SELECT id, price_date, source FROM flv_ceasa_prices").fetchall()
    for rid, price_date, source in rows:
        iso = normalize_date(price_date)
        is_syn, quality = quality_for_source(source)
        if iso:
            conn.execute(
                "UPDATE flv_ceasa_prices SET price_date=?, is_synthetic=?, data_quality=? WHERE id=?",
                (iso, is_syn, quality, rid),
            )
            changed += 1
        else:
            conn.execute(
                "UPDATE flv_ceasa_prices SET is_synthetic=?, data_quality=? WHERE id=?",
                (is_syn, "invalid_date", rid),
            )
    return changed


def _mark_quality(conn, table):
    if not _has_table(conn, table) or "source" not in _cols(conn, table):
        return 0
    rows = conn.execute(f"SELECT id, source FROM {table}").fetchall()
    for rid, source in rows:
        is_syn, quality = quality_for_source(source)
        conn.execute(f"UPDATE {table} SET is_synthetic=?, data_quality=? WHERE id=?", (is_syn, quality, rid))
    return len(rows)


def _clean_global_climate(conn):
    if not _has_table(conn, "flv_global_climate"):
        return 0
    cur = conn.execute("DELETE FROM flv_global_climate WHERE oni IS NULL AND atl_north_warm_idx IS NULL")
    return cur.rowcount


def _clean_macro(conn):
    if not _has_table(conn, "flv_macro_indicators"):
        return 0
    changed = 0
    rows = conn.execute("SELECT id, ipca_yoy_pct, selic_pct FROM flv_macro_indicators").fetchall()
    for rid, ipca, selic in rows:
        ipca2 = valid_percent(ipca, low=-10, high=30) if ipca is not None else None
        selic2 = valid_percent(selic, low=0, high=50) if selic is not None else None
        if ipca2 != ipca or selic2 != selic:
            conn.execute("UPDATE flv_macro_indicators SET ipca_yoy_pct=?, selic_pct=? WHERE id=?", (ipca2, selic2, rid))
            changed += 1
    return changed


def migrate(path):
    conn = sqlite3.connect(path)
    try:
        _add_quality_columns(conn)
        prices = _normalize_prices(conn)
        marked = sum(_mark_quality(conn, t) for t in TABLES if t != "flv_ceasa_prices")
        removed_global = _clean_global_climate(conn)
        cleaned_macro = _clean_macro(conn)
        conn.commit()
        print(f"{path}: prices_normalized={prices}, rows_marked={marked}, empty_global_removed={removed_global}, macro_cleaned={cleaned_macro}")
    finally:
        conn.close()


if __name__ == "__main__":
    for path in DB_CANDIDATES:
        if os.path.exists(path):
            migrate(path)
