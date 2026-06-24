"""FLV Database Layer — SQLite WAL mode, thread-safe."""
import sqlite3, os, json, time

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Prefer the populated production database under /data. Older builds left empty
# nia_flv.db files in the root and inside /flv, which caused HTTP 500 in IA/Audit.
def _select_db_path():
    candidates = [
        os.environ.get('NIAS_DB_PATH'),
        os.path.join(ROOT_PATH, 'data', 'nia_flv.db'),
        os.path.join(ROOT_PATH, 'nia_flv.db'),
        os.path.join(ROOT_PATH, 'flv', 'nia_flv.db'),
    ]
    for cand in candidates:
        if cand and os.path.exists(cand) and os.path.getsize(cand) > 8192:
            return cand
    return os.path.join(ROOT_PATH, 'data', 'nia_flv.db')

DB_PATH = _select_db_path()
SCHEMA_PATH = os.path.join(ROOT_PATH, 'data', 'flv_schema.sql')
if not os.path.exists(SCHEMA_PATH):
    SCHEMA_PATH = os.path.join(ROOT_PATH, 'flv_schema.sql')

_conn_cache = {}
_schema_checked = False


def get_conn():
    global _schema_checked
    tid = id(os.getpid())
    if tid not in _conn_cache:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        if not _schema_checked:
            try:
                from flv.db_migration import ensure_runtime_schema
                ensure_runtime_schema(conn)
                _schema_checked = True
            except Exception as e:
                print(f'[FLV] schema migration warning: {e}')
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
    from flv.data_quality import normalize_date, valid_price, quality_for_source
    price_date = normalize_date(price_date)
    price_avg = valid_price(price_avg)
    price_min = valid_price(price_min) if price_min is not None else None
    price_max = valid_price(price_max) if price_max is not None else None
    if not price_date or price_avg is None:
        return
    is_synthetic, data_quality = quality_for_source(source)
    conn = get_conn()
    cid = conn.execute("SELECT id FROM flv_cultures WHERE slug=?", (culture_slug,)).fetchone()
    if not cid:
        return
    conn.execute(
        "INSERT OR REPLACE INTO flv_ceasa_prices (culture_id,terminal,price_date,price_avg,price_min,price_max,volume_kg,source,is_synthetic,data_quality) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (cid['id'], terminal, price_date, price_avg, price_min, price_max, volume_kg, source, is_synthetic, data_quality)
    )
    conn.commit()

def upsert_climate(ibge_code, obs_date, temp_max=None, temp_min=None, precip=None, humidity=None, wind=None, source='INMET'):
    from flv.data_quality import normalize_date, quality_for_source
    obs_date = normalize_date(obs_date)
    if not obs_date:
        return
    is_synthetic, data_quality = quality_for_source(source)
    conn = get_conn()
    mid = conn.execute("SELECT id FROM flv_municipalities WHERE ibge_code=?", (ibge_code,)).fetchone()
    if not mid:
        return
    conn.execute(
        "INSERT OR REPLACE INTO flv_climate (mun_id,obs_date,temp_max_c,temp_min_c,precip_mm,humidity_pct,wind_ms,source,is_synthetic,data_quality) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (mid['id'], obs_date, temp_max, temp_min, precip, humidity, wind, source, is_synthetic, data_quality)
    )
    conn.commit()

def upsert_ndvi(ibge_code, obs_date, ndvi_value, ndvi_anomaly=None, source='SATVeg'):
    from flv.data_quality import normalize_date, quality_for_source
    obs_date = normalize_date(obs_date)
    try:
        ndvi_value = float(ndvi_value)
    except Exception:
        return
    if not obs_date or ndvi_value < 0 or ndvi_value > 1:
        return
    is_synthetic, data_quality = quality_for_source(source)
    conn = get_conn()
    mid = conn.execute("SELECT id FROM flv_municipalities WHERE ibge_code=?", (ibge_code,)).fetchone()
    if not mid:
        return
    conn.execute(
        "INSERT OR REPLACE INTO flv_ndvi (mun_id,obs_date,ndvi_value,ndvi_anomaly,source,is_synthetic,data_quality) VALUES (?,?,?,?,?,?,?)",
        (mid['id'], obs_date, ndvi_value, ndvi_anomaly, source, is_synthetic, data_quality)
    )
    conn.commit()

def upsert_macro_indicators(
    obs_date,
    diesel_brl_l=None,
    diesel_change_pct=None,
    brent_usd=None,
    brent_change_pct=None,
    wti_usd=None,
    wti_change_pct=None,
    usd_brl=None,
    selic_pct=None,
    ipca_yoy_pct=None,
    source='BCB/ANP'
):
    from flv.data_quality import normalize_date, valid_percent, quality_for_source
    obs_date = normalize_date(obs_date)
    if not obs_date:
        return
    ipca_yoy_pct = valid_percent(ipca_yoy_pct, low=-10.0, high=30.0) if ipca_yoy_pct is not None else None
    selic_pct = valid_percent(selic_pct, low=0.0, high=50.0) if selic_pct is not None else None
    is_synthetic, data_quality = quality_for_source(source)
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO flv_macro_indicators ("
        "obs_date,diesel_brl_l,diesel_change_pct,brent_usd,brent_change_pct,wti_usd,wti_change_pct,"
        "usd_brl,selic_pct,ipca_yoy_pct,source,is_synthetic,data_quality"
        ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            obs_date,
            diesel_brl_l,
            diesel_change_pct,
            brent_usd,
            brent_change_pct,
            wti_usd,
            wti_change_pct,
            usd_brl,
            selic_pct,
            ipca_yoy_pct,
            source,
            is_synthetic,
            data_quality,
        )
    )
    conn.commit()

def insert_news_event(obs_ts, source=None, title=None, url=None, risk_score=None, tags_json=None):
    conn = get_conn()
    conn.execute(
        "INSERT INTO flv_news_events (obs_ts,source,title,url,risk_score,tags_json) VALUES (?,?,?,?,?,?)",
        (obs_ts, source, title, url, risk_score, tags_json),
    )
    conn.commit()

def upsert_news_risk_daily(obs_date, risk_index, top_tags_json=None, sources_json=None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO flv_news_risk_daily (obs_date,risk_index,top_tags_json,sources_json) VALUES (?,?,?,?)",
        (obs_date, risk_index, top_tags_json, sources_json),
    )
    conn.commit()

def upsert_global_climate(obs_date, oni=None, atl_north_warm_idx=None, source="NOAA/ESRL"):
    from flv.data_quality import normalize_date, quality_for_source
    obs_date = normalize_date(obs_date)
    if not obs_date or (oni is None and atl_north_warm_idx is None):
        return
    is_synthetic, data_quality = quality_for_source(source)
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO flv_global_climate (obs_date,oni,atl_north_warm_idx,source,is_synthetic,data_quality) VALUES (?,?,?,?,?,?)",
        (obs_date, oni, atl_north_warm_idx, source, is_synthetic, data_quality),
    )
    conn.commit()

def query(sql, params=()):
    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        # Old deployments may have a populated DB without quality columns.
        # Apply migration once and retry, so APIs do not fail with HTTP 500.
        if 'no such column' in str(e).lower():
            from flv.db_migration import ensure_runtime_schema
            ensure_runtime_schema(conn)
            rows = conn.execute(sql, params).fetchall()
        else:
            raise
    return [dict(r) for r in rows]

def execute(sql, params=()):
    conn = get_conn()
    try:
        conn.execute(sql, params)
    except sqlite3.OperationalError as e:
        if 'no such column' in str(e).lower():
            from flv.db_migration import ensure_runtime_schema
            ensure_runtime_schema(conn)
            conn.execute(sql, params)
        else:
            raise
    conn.commit()
