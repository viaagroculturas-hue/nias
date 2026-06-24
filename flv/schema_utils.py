"""Utilidades para introspecção de schema SQLite."""
from __future__ import annotations
import sqlite3


def columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Retorna lista de nomes de colunas de uma tabela."""
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return [r[1] if isinstance(r, tuple) else r['name'] for r in rows]
    except Exception:
        return []


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Verifica se a tabela existe no banco."""
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        ).fetchone()
        return (row[0] if isinstance(row, tuple) else row[0]) > 0
    except Exception:
        return False
