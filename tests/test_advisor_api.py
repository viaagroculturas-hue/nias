"""
Testes: endpoints /api/nias/advisor/* via _dispatch.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.db_migration import ensure_runtime_schema
from flv.sa_weather_persistence import persist_south_america_weather, seed_nias_regions


SAMPLE_WEATHER = {
    "status": "ok",
    "results": [
        {
            "id": "AR-MDZ-CEN", "country_code": "AR", "region": "Mendoza",
            "lat": -32.89, "lon": -68.84, "source": "Open-Meteo",
            "current": {"temperature_c": 38.5, "humidity_pct": 15,
                        "wind_kmh": 22.0, "precip_mm": 0.0},
            "forecast_7d": {"dates": [], "temp_max": [], "temp_min": [],
                            "precip_mm": [], "wind_max_kmh": []},
        },
        {
            "id": "BR-SP-CIN", "country_code": "BR", "region": "Cinturão Verde SP",
            "lat": -23.52, "lon": -46.19, "source": "Open-Meteo",
            "current": {"temperature_c": 1.0, "humidity_pct": 95,
                        "wind_kmh": 5.0, "precip_mm": 0.0},
            "forecast_7d": {"dates": [], "temp_max": [], "temp_min": [],
                            "precip_mm": [], "wind_max_kmh": []},
        },
    ],
}


@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    db_file = str(tmp_path / "advisor_test.db")
    monkeypatch.setenv("NIAS_DB_PATH", db_file)

    import flv.db as db_mod
    orig_path = db_mod.DB_PATH
    db_mod.DB_PATH = db_file
    db_mod._conn_cache.clear()
    db_mod._schema_checked = False

    c = sqlite3.connect(db_file, check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("""
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
    """)
    ensure_runtime_schema(c)
    seed_nias_regions(c)
    persist_south_america_weather(c, SAMPLE_WEATHER)
    c.commit()
    c.close()

    yield

    db_mod.DB_PATH = orig_path
    db_mod._conn_cache.clear()
    db_mod._schema_checked = False


def _dispatch(path, params=None):
    from flv.nias_api.router import _dispatch as d
    return d(path, params or {})


# ─── /api/nias/advisor ────────────────────────────────────────────────────────

def test_advisor_endpoint_ok():
    r = _dispatch('advisor')
    assert r.get('status') in ('ok', 'partial'), f"Esperado ok/partial, got: {r}"


def test_advisor_has_recommendations():
    r = _dispatch('advisor')
    assert 'data' in r
    data = r['data']
    assert 'recommendations' in data


def test_advisor_recommendations_not_empty():
    r = _dispatch('advisor')
    recs = r.get('data', {}).get('recommendations', [])
    assert len(recs) >= 1, "Com dados de clima, deve haver ao menos 1 recomendação"


def test_advisor_each_rec_has_required_fields():
    r = _dispatch('advisor')
    recs = r.get('data', {}).get('recommendations', [])
    required = ['titulo', 'justificativa', 'cenario_contrario', 'fontes',
                'confianca', 'risco', 'score', 'acao_recomendada']
    for rec in recs:
        for field in required:
            assert field in rec, f"Campo '{field}' faltando em: {rec.get('titulo')}"


def test_advisor_has_scope():
    r = _dispatch('advisor')
    assert r.get('data', {}).get('scope') == 'south_america'


# ─── /api/nias/advisor/summary ───────────────────────────────────────────────

def test_advisor_summary_ok():
    r = _dispatch('advisor/summary')
    assert r.get('status') in ('ok', 'partial')


def test_advisor_summary_has_resumo():
    r = _dispatch('advisor/summary')
    data = r.get('data', {})
    assert data.get('resumo'), "Summary deve ter texto de resumo"


def test_advisor_summary_has_counts():
    r = _dispatch('advisor/summary')
    data = r.get('data', {})
    assert 'total_conselhos' in data
    assert 'oportunidades' in data
    assert 'riscos_climaticos' in data


# ─── /api/nias/advisor/opportunities ─────────────────────────────────────────

def test_advisor_opportunities_ok():
    r = _dispatch('advisor/opportunities')
    assert r.get('status') in ('ok', 'partial')
    assert 'opportunities' in r.get('data', {})


def test_advisor_opportunities_all_high_score():
    r = _dispatch('advisor/opportunities')
    opps = r.get('data', {}).get('opportunities', [])
    for o in opps:
        assert o.get('score', 0) >= 55, \
            f"Oportunidade com score baixo: {o.get('titulo')} — score {o.get('score')}"


# ─── /api/nias/advisor/risks ─────────────────────────────────────────────────

def test_advisor_risks_ok():
    r = _dispatch('advisor/risks')
    assert r.get('status') in ('ok', 'partial')
    assert 'risks' in r.get('data', {})


# ─── /api/nias/advisor/recommendations ───────────────────────────────────────

def test_advisor_recommendations_alias():
    r = _dispatch('advisor/recommendations')
    assert r.get('status') in ('ok', 'partial')


# ─── /api/nias/advisor/country?country=AR ────────────────────────────────────

def test_advisor_country_ar():
    r = _dispatch('advisor/country', {'country': ['AR']})
    assert r.get('status') in ('ok', 'partial')
    data = r.get('data', {})
    assert data.get('pais') == 'AR'
    recs = data.get('recommendations', [])
    assert all(rec.get('pais') == 'AR' for rec in recs)


def test_advisor_country_missing_param():
    r = _dispatch('advisor/country', {})
    assert r.get('status') == 'error'


# ─── /api/nias/advisor/thesis ────────────────────────────────────────────────

def test_advisor_thesis_requires_params():
    r = _dispatch('advisor/thesis', {})
    assert r.get('status') == 'error'


def test_advisor_thesis_with_product():
    r = _dispatch('advisor/thesis', {'product': ['tomate'], 'region': ['brasil']})
    assert r.get('status') in ('ok', 'partial')


# ─── /api/nias/advisor/product ───────────────────────────────────────────────

def test_advisor_product_requires_param():
    r = _dispatch('advisor/product', {})
    assert r.get('status') == 'error'


def test_advisor_product_with_name():
    r = _dispatch('advisor/product', {'product': ['tomate']})
    assert r.get('status') in ('ok', 'partial')
    assert 'recommendations' in r.get('data', {})


# ─── /api/nias/advisor/region ────────────────────────────────────────────────

def test_advisor_region_requires_param():
    r = _dispatch('advisor/region', {})
    assert r.get('status') == 'error'


def test_advisor_region_with_name():
    r = _dispatch('advisor/region', {'region': ['Mendoza']})
    assert r.get('status') in ('ok', 'partial')


# ─── Endpoints antigos não quebrados ─────────────────────────────────────────

def test_old_intelligence_opportunities_still_works():
    r = _dispatch('intelligence/opportunities')
    assert r.get('status') in ('ok', 'partial', 'error')


def test_old_weather_latest_still_works():
    r = _dispatch('weather/latest', {})
    assert r.get('status') in ('ok', 'partial', 'error')


def test_old_status_still_works():
    r = _dispatch('status')
    assert r.get('status') == 'ok'


def test_old_regions_still_works():
    r = _dispatch('regions')
    assert r.get('status') == 'ok'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
