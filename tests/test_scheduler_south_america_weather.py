"""
Testes: integração SA weather no pipeline/scheduler.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.db_migration import ensure_runtime_schema


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("""
        CREATE TABLE flv_climate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER,
            obs_date TEXT,
            temp_max_c REAL, temp_min_c REAL, precip_mm REAL,
            humidity_pct REAL, wind_ms REAL, insolation_h REAL,
            source TEXT, is_synthetic INTEGER DEFAULT 0,
            data_quality TEXT DEFAULT 'official_or_observed',
            scope TEXT DEFAULT 'brazil', country_code TEXT,
            region_id TEXT, region_name TEXT, lat REAL, lon REAL
        )
    """)
    ensure_runtime_schema(c)
    yield c
    c.close()


def test_pipeline_has_sa_weather_step():
    """pipeline.py deve conter chamada ao SA weather cycle."""
    src = open(
        os.path.join(os.path.dirname(__file__), '..', 'flv', 'pipeline.py'),
        encoding='utf-8'
    ).read()
    assert 'run_south_america_weather_cycle' in src, \
        "pipeline.py deve chamar run_south_america_weather_cycle"
    assert 'sa_weather_persistence' in src, \
        "pipeline.py deve importar sa_weather_persistence"


def test_pipeline_sa_step_after_inmet():
    """Passo SA deve vir após INMET (passo 2) no pipeline."""
    src = open(
        os.path.join(os.path.dirname(__file__), '..', 'flv', 'pipeline.py'),
        encoding='utf-8'
    ).read()
    inmet_pos = src.find('inmet_fetch')
    sa_pos    = src.find('run_south_america_weather_cycle')
    assert inmet_pos < sa_pos, "SA weather deve vir após INMET no pipeline"


def test_scheduler_has_sa_log_prefix():
    """O log do SA weather deve usar prefixo [OpenMeteo-SA]."""
    src = open(
        os.path.join(os.path.dirname(__file__), '..', 'flv', 'sa_weather_persistence.py'),
        encoding='utf-8'
    ).read()
    assert '[OpenMeteo-SA]' in src, "Deve usar prefixo [OpenMeteo-SA] nos logs"


def test_cycle_seeds_regions_before_weather(conn):
    """Ciclo deve seed os polos antes de buscar clima."""
    from unittest.mock import patch, MagicMock
    # Mock fetch para retornar status cached (sem chamar rede)
    mock_result = {"status": "cached", "results": [], "total_points": 0}
    import flv.openmeteo_batch_sa as om_mod
    original_cache = om_mod._cache
    original_last  = om_mod._last_fetch
    from datetime import datetime
    om_mod._cache     = mock_result
    om_mod._last_fetch = datetime.now()
    om_mod._rate_limited_until = None

    try:
        from flv.sa_weather_persistence import run_south_america_weather_cycle
        run_south_america_weather_cycle(conn)
        # Regiões devem ter sido seeded
        count = conn.execute("SELECT COUNT(*) FROM nias_regions WHERE active=1").fetchone()[0]
        assert count >= 40, f"Ciclo deve seed regiões, got {count}"
    finally:
        om_mod._cache     = original_cache
        om_mod._last_fetch = original_last


def test_cycle_skips_on_rate_limit(conn):
    """Ciclo não deve inserir registros quando rate limited."""
    import flv.openmeteo_batch_sa as mod
    from datetime import datetime, timedelta
    mod._rate_limited_until = datetime.now() + timedelta(hours=1)
    mod._cache = None
    mod._last_fetch = None
    try:
        from flv.sa_weather_persistence import run_south_america_weather_cycle
        result = run_south_america_weather_cycle(conn)
        assert result["status"] == "rate_limited"
        count = conn.execute(
            "SELECT COUNT(*) FROM flv_climate WHERE scope='south_america'"
        ).fetchone()[0]
        assert count == 0
    finally:
        mod._rate_limited_until = None


def test_db_migration_creates_nias_regions(conn):
    """ensure_runtime_schema deve criar tabela nias_regions."""
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert 'nias_regions' in tables, "nias_regions deve ser criada pela migration"


def test_db_migration_adds_sa_columns_to_flv_climate(conn):
    """ensure_runtime_schema deve adicionar colunas SA a flv_climate."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(flv_climate)").fetchall()}
    for col in ['scope', 'country_code', 'region_id', 'region_name', 'lat', 'lon']:
        assert col in cols, f"Coluna {col} deve existir em flv_climate"


def test_single_batch_request_not_per_polo():
    """O batch não deve fazer uma chamada por polo — deve usar uma única URL."""
    from flv.openmeteo_batch_sa import _build_url
    from flv.south_america_regions import get_weather_points
    points = get_weather_points()
    url = _build_url(points)
    # Uma única URL com todos os pontos
    assert url.count('https://api.open-meteo.com') == 1
    # Múltiplos pontos separados por vírgula
    lats = url.split('latitude=')[1].split('&')[0]
    assert ',' in lats, "Deve ter múltiplas latitudes separadas por vírgula (batch)"
    lat_count = len(lats.split(','))
    assert lat_count == len(points), f"URL deve ter {len(points)} latitudes, got {lat_count}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
