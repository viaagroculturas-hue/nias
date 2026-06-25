"""
Testes: endpoints de clima e inteligência sul-americanos da NIAS API.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.db_migration import ensure_runtime_schema
from flv.sa_weather_persistence import persist_south_america_weather, seed_nias_regions


def _dispatch(path, params=None):
    from flv.nias_api.router import _dispatch as d
    return d(path, params or {})


SAMPLE_WEATHER = {
    "status": "ok",
    "results": [
        {
            "id": "BR-SP-CIN", "country_code": "BR", "region": "Cinturão Verde SP",
            "lat": -23.52, "lon": -46.19, "source": "Open-Meteo",
            "current": {"temperature_c": 25.0, "humidity_pct": 65,
                        "wind_kmh": 12.0, "precip_mm": 0.0},
            "forecast_7d": {"dates": [], "temp_max": [], "temp_min": [],
                            "precip_mm": [], "wind_max_kmh": []},
        },
        {
            "id": "AR-MDZ-CEN", "country_code": "AR", "region": "Mendoza",
            "lat": -32.89, "lon": -68.84, "source": "Open-Meteo",
            "current": {"temperature_c": 38.0, "humidity_pct": 20,
                        "wind_kmh": 25.0, "precip_mm": 0.0},
            "forecast_7d": {"dates": [], "temp_max": [38.5], "temp_min": [22.0],
                            "precip_mm": [0.0], "wind_max_kmh": [30.0]},
        },
        {
            "id": "PE-ICA-EXP", "country_code": "PE", "region": "Ica",
            "lat": -14.07, "lon": -75.73, "source": "Open-Meteo",
            "current": {"temperature_c": 20.0, "humidity_pct": 80,
                        "wind_kmh": 10.0, "precip_mm": 2.0},
            "forecast_7d": {"dates": [], "temp_max": [], "temp_min": [],
                            "precip_mm": [], "wind_max_kmh": []},
        },
    ],
}


@pytest.fixture(autouse=True)
def seed_db_with_sa_weather(tmp_path, monkeypatch):
    """
    Cria banco temporário com dados SA e redireciona NIAS_DB_PATH.
    Garante que os testes de API leiam dados reais do banco.
    """
    db_file = str(tmp_path / "test_nias.db")
    monkeypatch.setenv("NIAS_DB_PATH", db_file)

    # Resetar cache de db.py
    import flv.db as db_mod
    original_path = db_mod.DB_PATH
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

    db_mod.DB_PATH = original_path
    db_mod._conn_cache.clear()
    db_mod._schema_checked = False


# ─── /api/nias/weather/south-america ─────────────────────────────────────────

def test_weather_south_america_returns_ok():
    r = _dispatch("weather/south-america")
    assert r.get("status") == "ok", f"Esperado ok, got: {r.get('status')}"


def test_weather_south_america_has_scope():
    r = _dispatch("weather/south-america")
    data = r.get("data", {})
    assert data.get("scope") == "south_america"


def test_weather_south_america_has_items():
    r = _dispatch("weather/south-america")
    items = r.get("data", {}).get("items", [])
    assert len(items) >= 1


def test_weather_south_america_has_country_codes():
    r = _dispatch("weather/south-america")
    items = r.get("data", {}).get("items", [])
    codes = {i.get("country_code") for i in items}
    assert "BR" in codes
    assert "AR" in codes


def test_weather_south_america_source_mode_persisted():
    r = _dispatch("weather/south-america")
    data = r.get("data", {})
    assert data.get("source_mode") == "persisted_db", \
        "Com dados no banco, source_mode deve ser 'persisted_db'"


# ─── /api/nias/weather/latest?country=BR ─────────────────────────────────────

def test_weather_latest_country_br():
    r = _dispatch("weather/latest", {"country": ["BR"]})
    assert r.get("status") in ("ok", "partial")
    data = r.get("data", {})
    assert data.get("scope") == "south_america"
    assert data.get("country") == "BR"


def test_weather_latest_country_ar():
    r = _dispatch("weather/latest", {"country": ["AR"]})
    assert r.get("status") in ("ok", "partial")
    data = r.get("data", {})
    assert data.get("country") == "AR"
    if r.get("status") == "ok":
        items = data.get("items", [])
        assert all(i.get("country_code") == "AR" for i in items)


def test_weather_latest_default_brazil_not_broken():
    """Sem filtro, retorna dados Brasil (mun_id based) sem erro."""
    r = _dispatch("weather/latest", {})
    # Deve retornar ok ou partial (sem exceção)
    assert r.get("status") in ("ok", "partial"), \
        "Endpoint padrão não deve quebrar"


# ─── /api/nias/intelligence/weather-price?scope=south_america ────────────────

def test_intelligence_wp_scope_south_america():
    r = _dispatch("intelligence/weather-price", {"scope": ["south_america"]})
    assert r.get("status") in ("ok", "partial")
    data = r.get("data", {})
    assert data.get("scope") == "south_america"


def test_intelligence_wp_scope_sa_has_items():
    r = _dispatch("intelligence/weather-price", {"scope": ["south_america"]})
    if r.get("status") == "ok":
        items = r.get("data", {}).get("items", [])
        assert len(items) >= 1


def test_intelligence_wp_country_ar():
    r = _dispatch("intelligence/weather-price", {"country": ["AR"]})
    assert r.get("status") in ("ok", "partial")
    data = r.get("data", {})
    assert data.get("country") == "AR"


def test_intelligence_wp_sa_no_fake_price():
    """A análise SA não deve inventar preço — deve dizer 'sem preço local'."""
    r = _dispatch("intelligence/weather-price", {"scope": ["south_america"]})
    if r.get("status") == "ok":
        items = r.get("data", {}).get("items", [])
        for item in items:
            price_signal = item.get("price_signal", "")
            assert "sem preço local" in price_signal or "não" in price_signal or price_signal == "", \
                f"Não deve inventar preço: {price_signal}"


def test_intelligence_wp_ar_calor_extremo():
    """Mendoza com 38°C deve gerar sinal de calor extremo."""
    r = _dispatch("intelligence/weather-price", {"country": ["AR"]})
    if r.get("status") == "ok":
        items = r.get("data", {}).get("items", [])
        mendoza = [i for i in items if "Mendoza" in i.get("region", "")]
        if mendoza:
            assert "calor extremo" in mendoza[0].get("weather_signal", ""), \
                "38°C em Mendoza deve gerar sinal 'calor extremo'"


def test_intelligence_wp_brazil_not_broken():
    """Filtro country=BR via rota padrão não deve quebrar."""
    r = _dispatch("intelligence/weather-price", {"country": ["BR"]})
    # Deve retornar ok ou partial sem exceção
    assert r.get("status") in ("ok", "partial")


# ─── /api/nias/regions ───────────────────────────────────────────────────────

def test_regions_south_america_has_all_countries():
    r = _dispatch("regions")
    assert r.get("status") == "ok"
    by_country = r.get("data", {}).get("by_country", {})
    for cc in ["BR", "AR", "CL", "PE", "BO", "PY", "UY"]:
        assert cc in by_country, f"País {cc} deve estar nas regiões"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
