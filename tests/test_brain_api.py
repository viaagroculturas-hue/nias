"""
Testes: endpoints /api/nias/brain/* via router._dispatch.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.db_migration import ensure_runtime_schema
from flv.sa_price_persistence import ensure_sa_prices_table, persist_country_prices

WEATHER_ROWS = [
    ('AR','Mendoza','AR-MDZ','-32.89','-68.84','2026-06-25',39.0,-1.0,0.0,30.0,10.0,'Open-Meteo'),
    ('CL','Maule','CL-MAU','-35.42','-71.65','2026-06-25',20.0,4.0,10.0,12.0,65.0,'Open-Meteo'),
]

PRICE_CL = {
    'country_code':'CL','status':'success','records':1,
    'items':[{
        'country_code':'CL','country':'Chile','market_name':'ODEPA',
        'market_type':'atacado','product':'tomate','product_normalized':'tomate',
        'category':'hortifruti','price':850.0,'currency':'CLP','unit':'kg',
        'price_per_kg':850.0,'price_usd':0.91,'date':'2026-06-25','source':'ODEPA',
        'source_url':'','source_type':'real','confidence':'baixa','is_fallback':0,
        'collected_at':'2026-06-25T10:00:00',
    }],
}


_CLIMATE_DDL = """
CREATE TABLE IF NOT EXISTS flv_climate (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mun_id INTEGER, obs_date TEXT,
    temp_max_c REAL, temp_min_c REAL, precip_mm REAL,
    humidity_pct REAL, wind_ms REAL, insolation_h REAL,
    source TEXT, is_synthetic INTEGER DEFAULT 0,
    data_quality TEXT DEFAULT 'official_or_observed',
    scope TEXT DEFAULT 'brazil', country_code TEXT,
    region_id TEXT, region_name TEXT, lat REAL, lon REAL
)
"""


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / 'brain_test.db')
    monkeypatch.setenv('NIAS_DB_PATH', db_file)

    import flv.db as db_mod
    orig = db_mod.DB_PATH
    db_mod.DB_PATH = db_file
    db_mod._conn_cache.clear()
    db_mod._schema_checked = False

    c = sqlite3.connect(db_file, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute(_CLIMATE_DDL)
    ensure_runtime_schema(c)
    for row in WEATHER_ROWS:
        c.execute("""
            INSERT INTO flv_climate
              (country_code,region_name,region_id,lat,lon,obs_date,
               temp_max_c,temp_min_c,precip_mm,wind_ms,humidity_pct,source,scope)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'south_america')
        """, row)
    c.commit()
    ensure_sa_prices_table(c)
    persist_country_prices(c, PRICE_CL)
    c.commit()
    c.close()

    yield

    db_mod.DB_PATH = orig
    db_mod._conn_cache.clear()
    db_mod._schema_checked = False


def _dispatch(path, params=None):
    from flv.nias_api.router import _dispatch as d
    return d(path, params or {})


# ─── /api/nias/brain ─────────────────────────────────────────────────────────

def test_brain_summary_ok():
    r = _dispatch('brain')
    assert r['status'] in ('ok', 'partial')


def test_brain_summary_has_health():
    r = _dispatch('brain')
    assert 'health' in r.get('data', {})


def test_brain_summary_has_events():
    r = _dispatch('brain')
    data = r.get('data', {})
    assert 'events_summary' in data


def test_brain_summary_has_decisions():
    r = _dispatch('brain')
    data = r.get('data', {})
    assert 'decisions_summary' in data


# ─── /api/nias/brain/pulse ───────────────────────────────────────────────────

def test_brain_pulse_ok():
    r = _dispatch('brain/pulse')
    assert r['status'] == 'ok'


def test_brain_pulse_has_sources():
    r = _dispatch('brain/pulse')
    data = r.get('data', {})
    assert 'sources' in data
    assert len(data['sources']) >= 1


def test_brain_pulse_has_health():
    r = _dispatch('brain/pulse')
    data = r.get('data', {})
    assert data.get('health') in ('saudavel','ok','atencao','degradado','desconhecido')


def test_brain_pulse_has_coverage():
    r = _dispatch('brain/pulse')
    data = r.get('data', {})
    assert 'coverage' in data


# ─── /api/nias/brain/events ──────────────────────────────────────────────────

def test_brain_events_ok():
    r = _dispatch('brain/events')
    assert r['status'] in ('ok', 'partial')


def test_brain_events_has_list():
    r = _dispatch('brain/events')
    data = r.get('data', {})
    assert 'events' in data
    assert isinstance(data['events'], list)


def test_brain_events_frost_present():
    r = _dispatch('brain/events')
    events = r.get('data', {}).get('events', [])
    frost = [e for e in events if 'geada' in e.get('tipo','')]
    assert len(frost) >= 1, 'Geada em AR deveria aparecer nos eventos'


def test_brain_events_filter_by_country():
    r = _dispatch('brain/events', {'country': ['AR']})
    data = r.get('data', {})
    events = data.get('events', [])
    for ev in events:
        if ev.get('pais') != 'SA':
            assert ev.get('pais') == 'AR', f'Evento de país {ev.get("pais")} inesperado'


def test_brain_events_have_required_fields():
    r = _dispatch('brain/events')
    events = r.get('data', {}).get('events', [])
    for ev in events[:5]:
        for f in ('id','tipo','gravidade','titulo','descricao','fonte'):
            assert f in ev, f'Campo {f!r} ausente no evento'


# ─── /api/nias/brain/decisions ───────────────────────────────────────────────

def test_brain_decisions_ok():
    r = _dispatch('brain/decisions')
    assert r['status'] in ('ok', 'partial')


def test_brain_decisions_has_list():
    r = _dispatch('brain/decisions')
    assert 'decisions' in r.get('data', {})


def test_brain_decisions_have_validity():
    r = _dispatch('brain/decisions')
    cards = r.get('data', {}).get('decisions', [])
    for c in cards:
        assert c.get('validade_ate'), 'Cartão sem validade_ate'


def test_brain_decisions_filter_by_tipo():
    r = _dispatch('brain/decisions', {'tipo': ['alerta']})
    cards = r.get('data', {}).get('decisions', [])
    for c in cards:
        assert c.get('tipo') == 'alerta', f"Filtro 'alerta' retornou tipo={c.get('tipo')}"


def test_brain_decisions_have_note():
    r = _dispatch('brain/decisions')
    data = r.get('data', {})
    assert data.get('note'), 'Endpoint decisions deve ter nota explicativa'


# ─── /api/nias/brain/radar ───────────────────────────────────────────────────

def test_brain_radar_ok():
    r = _dispatch('brain/radar')
    assert r['status'] in ('ok', 'partial')


def test_brain_radar_has_horizons():
    r = _dispatch('brain/radar')
    data = r.get('data', {})
    for h in ('agora', '24h', '7d', '30d'):
        assert h in data.get('radar', {}), f'Horizonte {h!r} ausente'


def test_brain_radar_has_data_note():
    r = _dispatch('brain/radar')
    data = r.get('data', {})
    assert data.get('data_note'), 'Radar deve ter data_note'


# ─── /api/nias/brain/thesis ──────────────────────────────────────────────────

def test_brain_thesis_by_country():
    r = _dispatch('brain/thesis', {'country': ['CL']})
    assert r['status'] == 'ok'
    data = r.get('data', {})
    assert data.get('status') == 'ok'


def test_brain_thesis_has_fontes():
    r = _dispatch('brain/thesis', {'country': ['CL']})
    data = r.get('data', {})
    assert data.get('fontes'), 'Tese sem fontes'


def test_brain_thesis_no_filter():
    r = _dispatch('brain/thesis', {})
    assert r['status'] in ('ok', 'partial')


def test_brain_thesis_unknown_country_sem_dado():
    r = _dispatch('brain/thesis', {'country': ['ZZ']})
    data = r.get('data', {})
    assert data.get('status') == 'sem_dado'


# ─── /api/nias/brain/quality ─────────────────────────────────────────────────

def test_brain_quality_ok():
    r = _dispatch('brain/quality')
    assert r['status'] == 'ok'


def test_brain_quality_has_cobertura():
    r = _dispatch('brain/quality')
    data = r.get('data', {})
    quality = data.get('quality', {})
    assert 'cobertura_clima' in quality
    assert 'cobertura_preco' in quality


def test_brain_quality_has_changes():
    r = _dispatch('brain/quality')
    data = r.get('data', {})
    assert 'changes' in data
    assert isinstance(data['changes'], list)


# ─── Rota não existe ─────────────────────────────────────────────────────────

def test_brain_nonexistent_route():
    r = _dispatch('brain/nonexistent')
    assert r['status'] == 'error'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
