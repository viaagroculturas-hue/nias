"""FLV Database Layer — SQLite WAL mode, thread-safe."""
import sqlite3, os, json, time

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'flv_schema.sql')

_conn_cache = {}

def get_conn():
    tid = id(os.getpid())
    if tid not in _conn_cache:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        _conn_cache[tid] = conn
    return _conn_cache[tid]

def init_db():
    conn = get_conn()
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        sql = f.read()
    for stmt in sql.split(';'):
        stmt = stmt.strip()
        if stmt and not stmt.upper().startswith('PRAGMA'):
            try:
                conn.execute(stmt)
            except Exception:
                pass
    conn.commit()
    _seed_cultures(conn)
    _seed_municipalities(conn)
    print(f'[FLV] DB inicializado: {DB_PATH}')

def _seed_cultures(conn):
    cultures = [
        ('tomate',   'Tomate Mesa',      'legume',  'R$/kg', '0133', 'TOMATE',          14, '{"pico":["jun","jul","ago"],"baixa":["dez","jan","fev"]}', 'GO,SP,MG,BA'),
        ('cebola',   'Cebola',           'legume',  'R$/kg', '0052', 'CEBOLA',          90, '{"pico":["dez","jan"],"baixa":["jun","jul"]}',             'SC,BA,SP,GO'),
        ('batata',   'Batata Inglesa',   'legume',  'R$/kg', '0020', 'BATATA INGLESA',  45, '{"pico":["abr","mai"],"baixa":["out","nov"]}',             'MG,SP,PR,BA'),
        ('pimentao', 'Pimentao',         'legume',  'R$/kg', '0106', 'PIMENTAO',        10, '{"pico":["jul","ago"],"baixa":["jan","fev"]}',             'SP,MG,PE,CE'),
        ('folhosas', 'Alface/Repolho',   'verdura', 'R$/kg', '0059', 'ALFACE',           4, '{"pico":["jun","jul"],"baixa":["dez","jan"]}',             'SP,MG,RJ,PR'),
        ('cenoura',  'Cenoura',          'legume',  'R$/kg', '0040', 'CENOURA',         30, '{"pico":["mai","jun"],"baixa":["nov","dez"]}',             'MG,SP,GO,BA'),
        ('manga',    'Manga',            'fruta',   'R$/kg', '0079', 'MANGA',           14, '{"pico":["nov","dez","jan"],"baixa":["mai","jun"]}',       'BA,PE,SP,MG'),
        ('uva',      'Uva de Mesa',      'fruta',   'R$/kg', '0145', 'UVA',             30, '{"pico":["dez","jan","fev"],"baixa":["jun","jul"]}',       'PE,BA,RS,SP'),
        ('banana',   'Banana',           'fruta',   'R$/kg', '0018', 'BANANA',          14, '{"pico":["mar","abr"],"baixa":["set","out"]}',             'BA,SP,MG,SC'),
        ('laranja',  'Laranja',          'fruta',   'R$/kg', '0083', 'LARANJA',         60, '{"pico":["jun","jul","ago"],"baixa":["dez","jan"]}',       'SP,BA,MG,SE'),
        ('morango',  'Morango',          'fruta',   'R$/kg', '0088', 'MORANGO',          4, '{"pico":["ago","set"],"baixa":["fev","mar"]}',             'MG,SP,RS,PR'),
        ('maca',     'Maca',             'fruta',   'R$/kg', '0075', 'MACA',            90, '{"pico":["fev","mar","abr"],"baixa":["set","out"]}',       'SC,RS,PR'),
        ('melao',    'Melao',            'fruta',   'R$/kg', '0080', 'MELAO',           21, '{"pico":["set","out","nov"],"baixa":["abr","mai"]}',       'RN,CE,BA,PE'),
        ('mamao',    'Mamao',            'fruta',   'R$/kg', '0076', 'MAMAO',            7, '{"pico":["jan","fev"],"baixa":["jul","ago"]}',             'BA,ES,CE,RN'),
        ('abacaxi',  'Abacaxi',          'fruta',   'R$/kg', '0001', 'ABACAXI',         14, '{"pico":["dez","jan","fev"],"baixa":["jun","jul"]}',       'PA,MG,PB,BA'),
        ('alho',     'Alho',             'legume',  'R$/kg', '0008', 'ALHO',           180, '{"pico":["nov","dez"],"baixa":["mai","jun"]}',             'MG,GO,SC,RS'),
    ]
    for c in cultures:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO flv_cultures (slug,name_pt,category,unit,sidra_code,conab_key,shelf_life_days,seasonality_json,main_producers) VALUES (?,?,?,?,?,?,?,?,?)",
                c
            )
        except Exception:
            pass
    conn.commit()

def _seed_municipalities(conn):
    muns = [
        ('2606101', 'Gravata',          'PE', -8.2044, -35.5620, 'CEASA-PE',  '82898'),
        ('3519055', 'Holambra',         'SP', -22.6347,-47.0597, 'CEAGESP',   'A711'),
        ('2611101', 'Petrolina',        'PE', -9.3891, -40.5028, 'CEASA-PE',  'A370'),
        ('2910800', 'Juazeiro',         'BA', -9.4163, -40.5001, 'CEASA-BA',  'A402'),
        ('3548906', 'Sao Paulo (CEAGESP)','SP',-23.5297,-46.7472,'CEAGESP',   'A701'),
        ('4322905', 'Vacaria',          'RS', -28.5033,-50.7764, 'CEASA-RS',  'A880'),
        ('3520509', 'Ibiuna',           'SP', -23.6567,-47.2225, 'CEAGESP',   'A711'),
        ('4208203', 'Ituporanga',       'SC', -27.4128,-49.5992, 'CEASA-SC',  'A863'),
    ]
    for m in muns:
        try:
            conn.execute(
                "INSERT OR IGNORE INTO flv_municipalities (ibge_code,name,state_uf,lat,lon,ceasa_ref,inmet_station) VALUES (?,?,?,?,?,?,?)",
                m
            )
        except Exception:
            pass
    conn.commit()

def upsert_price(culture_slug, terminal, price_date, price_avg, price_min=None, price_max=None, volume_kg=None, source='CONAB'):
    conn = get_conn()
    cid = conn.execute("SELECT id FROM flv_cultures WHERE slug=?", (culture_slug,)).fetchone()
    if not cid:
        return
    conn.execute(
        "INSERT OR REPLACE INTO flv_ceasa_prices (culture_id,terminal,price_date,price_avg,price_min,price_max,volume_kg,source) VALUES (?,?,?,?,?,?,?,?)",
        (cid['id'], terminal, price_date, price_avg, price_min, price_max, volume_kg, source)
    )
    conn.commit()

def upsert_climate(ibge_code, obs_date, temp_max=None, temp_min=None, precip=None, humidity=None, wind=None, source='INMET'):
    conn = get_conn()
    mid = conn.execute("SELECT id FROM flv_municipalities WHERE ibge_code=?", (ibge_code,)).fetchone()
    if not mid:
        return
    conn.execute(
        "INSERT OR REPLACE INTO flv_climate (mun_id,obs_date,temp_max_c,temp_min_c,precip_mm,humidity_pct,wind_ms,source) VALUES (?,?,?,?,?,?,?,?)",
        (mid['id'], obs_date, temp_max, temp_min, precip, humidity, wind, source)
    )
    conn.commit()

def upsert_ndvi(ibge_code, obs_date, ndvi_value, ndvi_anomaly=None, source='SATVeg'):
    conn = get_conn()
    mid = conn.execute("SELECT id FROM flv_municipalities WHERE ibge_code=?", (ibge_code,)).fetchone()
    if not mid:
        return
    conn.execute(
        "INSERT OR REPLACE INTO flv_ndvi (mun_id,obs_date,ndvi_value,ndvi_anomaly,source) VALUES (?,?,?,?,?)",
        (mid['id'], obs_date, ndvi_value, ndvi_anomaly, source)
    )
    conn.commit()

def query(sql, params=()):
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]

def execute(sql, params=()):
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()
