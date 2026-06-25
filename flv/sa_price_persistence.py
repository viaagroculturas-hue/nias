"""
NIAS — Persistência de preços sul-americanos no banco SQLite.

Tabela: nias_sa_prices (separada de flv_ceasa_prices para não interferir com BR).
Schema inclui todos os campos de normalização regional.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)

# DDL da tabela de preços sul-americanos
_SA_PRICES_DDL = """
CREATE TABLE IF NOT EXISTS nias_sa_prices (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code        TEXT NOT NULL,
    country             TEXT NOT NULL,
    market_name         TEXT,
    market_type         TEXT DEFAULT 'atacado',
    product             TEXT NOT NULL,
    product_normalized  TEXT,
    category            TEXT,
    price               REAL NOT NULL,
    currency            TEXT NOT NULL,
    unit                TEXT DEFAULT 'kg',
    price_per_kg        REAL,
    price_usd           REAL,
    price_date          TEXT NOT NULL,
    source              TEXT NOT NULL,
    source_url          TEXT,
    source_type         TEXT DEFAULT 'real',
    confidence          TEXT DEFAULT 'media',
    is_fallback         INTEGER DEFAULT 0,
    collected_at        TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(country_code, product_normalized, market_name, price_date, source)
)
"""


def ensure_sa_prices_table(conn: sqlite3.Connection) -> None:
    """Cria tabela nias_sa_prices se não existir."""
    conn.execute(_SA_PRICES_DDL)
    conn.commit()


def persist_country_prices(conn: sqlite3.Connection, result: dict) -> int:
    """
    Persiste registros de preços de um país no banco.
    Usa INSERT OR REPLACE para idempotência.
    Nunca afeta tabela flv_ceasa_prices (Brasil).
    Retorna número de registros inseridos/substituídos.
    """
    ensure_sa_prices_table(conn)

    items = result.get('items', [])
    if not items:
        return 0

    today = datetime.now().strftime('%Y-%m-%d')
    inserted = 0

    for item in items:
        try:
            conn.execute("""
                INSERT OR REPLACE INTO nias_sa_prices
                  (country_code, country, market_name, market_type,
                   product, product_normalized, category,
                   price, currency, unit, price_per_kg, price_usd,
                   price_date, source, source_url, source_type,
                   confidence, is_fallback, collected_at)
                VALUES (?,?,?,?, ?,?,?, ?,?,?,?,?, ?,?,?,?, ?,?,?)
            """, (
                item.get('country_code', ''),
                item.get('country', ''),
                item.get('market_name', ''),
                item.get('market_type', 'atacado'),
                item.get('product', ''),
                item.get('product_normalized', ''),
                item.get('category', ''),
                item.get('price', 0),
                item.get('currency', ''),
                item.get('unit', 'kg'),
                item.get('price_per_kg'),
                item.get('price_usd'),
                item.get('date', today),
                item.get('source', ''),
                item.get('source_url', ''),
                item.get('source_type', 'real'),
                item.get('confidence', 'media'),
                item.get('is_fallback', 0),
                item.get('collected_at', datetime.now().isoformat()),
            ))
            inserted += 1
        except sqlite3.Error as e:
            logger.warning('[SA-Prices] Erro ao inserir %s/%s: %s',
                           item.get('country_code'), item.get('product'), e)

    conn.commit()
    return inserted


def get_latest_sa_prices(conn: sqlite3.Connection,
                          country_code: str = None,
                          product_normalized: str = None) -> list[dict]:
    """
    Retorna preços mais recentes do banco SA.
    Filtra opcionalmente por país e/ou produto.
    """
    ensure_sa_prices_table(conn)

    try:
        filters = []
        args_sub  = []
        args_main = []

        if country_code:
            filters.append('country_code = ?')
            args_sub.append(country_code.upper())
            args_main.append(country_code.upper())

        if product_normalized:
            filters.append('product_normalized = ?')
            args_sub.append(product_normalized.lower())
            args_main.append(product_normalized.lower())

        where_clause = ('WHERE ' + ' AND '.join(filters)) if filters else ''
        sub_where    = ('WHERE ' + ' AND '.join(filters)) if filters else ''

        query = f"""
            SELECT country_code, country, market_name, market_type,
                   product, product_normalized, category,
                   price, currency, unit, price_per_kg, price_usd,
                   price_date, source, source_url, source_type,
                   confidence, is_fallback, collected_at
            FROM nias_sa_prices
            WHERE price_date = (
                SELECT MAX(price_date) FROM nias_sa_prices
                {sub_where}
            )
            {('AND ' + ' AND '.join(filters)) if filters else ''}
            ORDER BY country_code, product_normalized
        """

        rows = conn.execute(query, args_sub + args_main).fetchall()
        return [dict(r) for r in rows]

    except sqlite3.OperationalError as e:
        logger.warning('[SA-Prices] Query falhou: %s', e)
        return []


def get_sa_prices_summary(conn: sqlite3.Connection) -> dict:
    """Resumo agregado de preços SA no banco."""
    ensure_sa_prices_table(conn)
    try:
        row = conn.execute("""
            SELECT COUNT(*) as total,
                   MAX(price_date) as latest_date,
                   COUNT(DISTINCT country_code) as countries,
                   COUNT(DISTINCT product_normalized) as products
            FROM nias_sa_prices
        """).fetchone()
        by_country = {}
        for r in conn.execute("""
            SELECT country_code, country, COUNT(*) as records,
                   MAX(price_date) as latest_date, currency
            FROM nias_sa_prices
            GROUP BY country_code
            ORDER BY country_code
        """).fetchall():
            by_country[r['country_code']] = {
                'country':     r['country'],
                'records':     r['records'],
                'latest_date': r['latest_date'],
                'currency':    r['currency'],
            }
        return {
            'total_records': row['total'] if row else 0,
            'latest_date':   row['latest_date'] if row else None,
            'countries':     row['countries'] if row else 0,
            'products':      row['products'] if row else 0,
            'by_country':    by_country,
            'scope':         'south_america',
        }
    except sqlite3.OperationalError:
        return {'total_records': 0, 'latest_date': None, 'countries': 0, 'scope': 'south_america'}


def run_sa_prices_cycle(conn: sqlite3.Connection,
                         countries: list[str] = None,
                         force: bool = False) -> dict:
    """
    Ciclo completo: coleta → normaliza → persiste preços SA.
    BR é excluído (gerenciado por ceasa.py).
    Falha de um país não interrompe os demais.
    """
    from flv.collectors.prices.source_registry import collect_all_countries
    from flv.scheduler import _log as sched_log

    # Excluir BR (já gerenciado)
    from flv.south_america_price_sources import get_all_countries
    if countries is None:
        countries = [cc for cc in get_all_countries() if cc != 'BR']

    sched_log(f'[Prices-SA] START countries={len(countries)}: {",".join(countries)}')

    results = collect_all_countries(countries)
    summary = {}

    for cc, result in results.items():
        status  = result.get('status', 'error')
        records = result.get('records', 0)

        if status == 'success' and records > 0:
            persisted = persist_country_prices(conn, result)
            sched_log(f'[Prices-SA] {cc} success records={persisted}')
            summary[cc] = {'status': 'success', 'records': persisted}
        elif status in ('source_pending', 'source_not_available', 'managed_by_ceasa_collector'):
            sched_log(f'[Prices-SA] {cc} {status}')
            summary[cc] = {'status': status, 'records': 0}
        elif status in ('source_unreachable', 'source_no_data'):
            sched_log(f'[Prices-SA] {cc} {status}: {result.get("message", "")}')
            summary[cc] = {'status': status, 'records': 0, 'message': result.get('message')}
        else:
            sched_log(f'[Prices-SA] {cc} {status}: {result.get("message", "")}')
            summary[cc] = {'status': status, 'records': 0}

    total = sum(v.get('records', 0) for v in summary.values())
    sched_log(f'[Prices-SA] DONE total_records={total}')

    return {
        'status':    'done',
        'summary':   summary,
        'total':     total,
        'countries': list(summary.keys()),
        'scope':     'south_america',
    }
