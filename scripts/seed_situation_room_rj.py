"""Carrega base curada de recuperação judicial no SQLite local.
Opcional: usado apenas para compatibilidade com módulos antigos que leem flv_producers_rj.
"""
from __future__ import annotations
import json, os, sqlite3

ROOT = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(ROOT, 'data', 'nia_flv.db')
JSON_PATH = os.path.join(ROOT, 'data', 'situation_room', 'recovery_judicial_cases.json')

SCHEMA = '''
CREATE TABLE IF NOT EXISTS flv_producers_rj (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    cnpj TEXT UNIQUE,
    process_number TEXT,
    court TEXT,
    judicial_status TEXT,
    city TEXT,
    state_uf TEXT,
    lat REAL,
    lon REAL,
    products TEXT,
    production_volume TEXT,
    annual_revenue REAL,
    employees INTEGER,
    debts_total REAL,
    entry_date TEXT,
    status TEXT DEFAULT 'ativo',
    segment TEXT,
    last_judicial_update TEXT,
    process_status_detail TEXT,
    creditor_list TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
)
'''

with open(JSON_PATH, encoding='utf-8') as f:
    cases = json.load(f).get('cases', [])
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute(SCHEMA)
for c in cases:
    cur.execute('''
        INSERT OR REPLACE INTO flv_producers_rj
        (company_name, cnpj, process_number, court, judicial_status, city, state_uf, lat, lon, products,
         annual_revenue, employees, debts_total, entry_date, segment, last_judicial_update, process_status_detail, creditor_list, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    ''', (
        c.get('company_name'), c.get('cnpj'), c.get('process_number'), c.get('court'), c.get('judicial_status'),
        c.get('city'), c.get('state_uf'), c.get('lat'), c.get('lon'), json.dumps(c.get('products', []), ensure_ascii=False),
        c.get('annual_revenue'), c.get('employees'), c.get('debts_total'), c.get('entry_date'), c.get('segment'),
        c.get('last_judicial_update'), c.get('brazil_impact'), json.dumps(c.get('source_urls', []), ensure_ascii=False)
    ))
conn.commit()
conn.close()
print(f'Situation Room RJ atualizado: {len(cases)} casos curados carregados em {DB}')
