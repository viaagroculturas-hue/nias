"""
Testes: persistência de clima sul-americano no banco SQLite.
"""
import sys, os, sqlite3, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.sa_weather_persistence import (
    seed_nias_regions,
    get_nias_regions,
    persist_south_america_weather,
    get_latest_sa_weather,
    get_sa_weather_summary,
    run_south_america_weather_cycle,
)
from flv.db_migration import ensure_runtime_schema


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def conn():
    """Banco em memória com schema completo."""
    import pathlib, re
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    # Criar tabela flv_climate mínima (base + colunas SA)
    c.execute("""
        CREATE TABLE flv_climate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER,
            obs_date TEXT,
            temp_max_c REAL,
            temp_min_c REAL,
            precip_mm REAL,
            humidity_pct REAL,
            wind_ms REAL,
            insolation_h REAL,
            source TEXT,
            is_synthetic INTEGER DEFAULT 0,
            data_quality TEXT DEFAULT 'official_or_observed',
            scope TEXT DEFAULT 'brazil',
            country_code TEXT,
            region_id TEXT,
            region_name TEXT,
            lat REAL,
            lon REAL
        )
    """)
    ensure_runtime_schema(c)
    yield c
    c.close()


SAMPLE_WEATHER = {
    "status": "ok",
    "scope": "south_america",
    "results": [
        {
            "id": "BR-SP-CIN",
            "country_code": "BR",
            "region": "Cinturão Verde SP",
            "lat": -23.52, "lon": -46.19,
            "source": "Open-Meteo",
            "current": {
                "temperature_c": 22.0, "humidity_pct": 65,
                "wind_kmh": 12.0, "precip_mm": 0.0,
            },
            "forecast_7d": {
                "dates": [], "temp_max": [], "temp_min": [],
                "precip_mm": [], "wind_max_kmh": [],
            },
        },
        {
            "id": "AR-MDZ-CEN",
            "country_code": "AR",
            "region": "Mendoza",
            "lat": -32.89, "lon": -68.84,
            "source": "Open-Meteo",
            "current": {
                "temperature_c": 10.0, "humidity_pct": 45,
                "wind_kmh": 20.0, "precip_mm": 0.0,
            },
            "forecast_7d": {
                "dates": [], "temp_max": [], "temp_min": [],
                "precip_mm": [], "wind_max_kmh": [],
            },
        },
        {
            "id": "CL-OHI-FRU",
            "country_code": "CL",
            "region": "O'Higgins / Maule",
            "lat": -34.17, "lon": -70.74,
            "source": "Open-Meteo",
            "current": {
                "temperature_c": 8.0, "humidity_pct": 70,
                "wind_kmh": 8.0, "precip_mm": 5.0,
            },
            "forecast_7d": {
                "dates": [], "temp_max": [], "temp_min": [],
                "precip_mm": [], "wind_max_kmh": [],
            },
        },
    ],
}


# ─── Testes: nias_regions seed ───────────────────────────────────────────────

def test_seed_nias_regions_inserts_all(conn):
    count = seed_nias_regions(conn)
    assert count >= 40, f"Esperado >=40 polos, got {count}"


def test_seed_nias_regions_brazil_preserved(conn):
    seed_nias_regions(conn)
    br = get_nias_regions(conn, country_code="BR")
    assert len(br) >= 10, "Brasil deve ter ao menos 10 polos"


def test_seed_nias_regions_argentina_present(conn):
    seed_nias_regions(conn)
    ar = get_nias_regions(conn, country_code="AR")
    assert len(ar) >= 3


def test_seed_nias_regions_has_lat_lon(conn):
    seed_nias_regions(conn)
    regions = get_nias_regions(conn)
    for r in regions:
        assert r["lat"] is not None
        assert r["lon"] is not None
        assert r["country_code"] is not None


def test_seed_idempotent(conn):
    count1 = seed_nias_regions(conn)
    count2 = seed_nias_regions(conn)
    assert count1 == count2, "Seed deve ser idempotente (INSERT OR REPLACE)"
    total = conn.execute("SELECT COUNT(*) FROM nias_regions").fetchone()[0]
    assert total == count1, "Não deve duplicar registros"


# ─── Testes: persist_south_america_weather ──────────────────────────────────

def test_persist_inserts_records(conn):
    inserted = persist_south_america_weather(conn, SAMPLE_WEATHER)
    assert inserted == 3


def test_persist_sets_scope_south_america(conn):
    persist_south_america_weather(conn, SAMPLE_WEATHER)
    rows = conn.execute(
        "SELECT * FROM flv_climate WHERE scope='south_america'"
    ).fetchall()
    assert len(rows) == 3
    for r in rows:
        assert dict(r)["scope"] == "south_america"


def test_persist_preserves_country_code(conn):
    persist_south_america_weather(conn, SAMPLE_WEATHER)
    ar = conn.execute(
        "SELECT * FROM flv_climate WHERE country_code='AR'"
    ).fetchall()
    assert len(ar) == 1
    assert dict(ar[0])["region_name"] == "Mendoza"


def test_persist_does_not_touch_mun_id_records(conn):
    # Inserir registro BR existente com mun_id
    conn.execute("""
        INSERT INTO flv_climate (mun_id, obs_date, temp_max_c, source)
        VALUES (3550308, '2026-06-25', 28.5, 'INMET')
    """)
    conn.commit()
    persist_south_america_weather(conn, SAMPLE_WEATHER)
    # Registro original deve existir
    old = conn.execute(
        "SELECT * FROM flv_climate WHERE mun_id=3550308"
    ).fetchone()
    assert old is not None, "Registro BR com mun_id deve ser preservado"


def test_persist_idempotent(conn):
    i1 = persist_south_america_weather(conn, SAMPLE_WEATHER)
    i2 = persist_south_america_weather(conn, SAMPLE_WEATHER)
    total = conn.execute(
        "SELECT COUNT(*) FROM flv_climate WHERE scope='south_america'"
    ).fetchone()[0]
    assert total == 3, f"Persist idempotente: esperado 3, got {total}"


# ─── Testes: queries ─────────────────────────────────────────────────────────

def test_get_latest_sa_weather_all(conn):
    persist_south_america_weather(conn, SAMPLE_WEATHER)
    items = get_latest_sa_weather(conn)
    assert len(items) == 3


def test_get_latest_sa_weather_by_country(conn):
    persist_south_america_weather(conn, SAMPLE_WEATHER)
    br_items = get_latest_sa_weather(conn, country_code="BR")
    assert len(br_items) == 1
    assert br_items[0]["country_code"] == "BR"


def test_get_sa_weather_summary(conn):
    persist_south_america_weather(conn, SAMPLE_WEATHER)
    s = get_sa_weather_summary(conn)
    assert s["total_records"] == 3
    assert s["countries"] == 3
    assert s["scope"] == "south_america"
    assert s["latest_date"] is not None


# ─── Teste: ciclo integrado com mock ────────────────────────────────────────

def test_run_cycle_rate_limited(conn, monkeypatch):
    """Ciclo deve retornar status=rate_limited sem persistir."""
    from datetime import datetime, timedelta
    import flv.openmeteo_batch_sa as mod
    mod._rate_limited_until = datetime.now() + timedelta(hours=1)
    try:
        result = run_south_america_weather_cycle(conn)
        assert result["status"] == "rate_limited"
        total = conn.execute(
            "SELECT COUNT(*) FROM flv_climate WHERE scope='south_america'"
        ).fetchone()[0]
        assert total == 0, "Não deve persistir quando rate limited"
    finally:
        mod._rate_limited_until = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
