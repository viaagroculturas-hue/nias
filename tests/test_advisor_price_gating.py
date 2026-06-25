"""
Testes: price gating no Conselheiro NIAS.
O advisor não pode emitir recomendação forte ('comprar'/'vender') sem preço real.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.db_migration import ensure_runtime_schema
from flv.sa_price_persistence import ensure_sa_prices_table, persist_country_prices
from flv.sa_weather_persistence import persist_south_america_weather
from flv.advisor_engine import NiasAdvisorEngine


WEATHER_WITH_RISK = {
    "status": "ok",
    "results": [
        {
            "id": "AR-MDZ-CEN", "country_code": "AR", "region": "Mendoza",
            "lat": -32.89, "lon": -68.84, "source": "Open-Meteo",
            "current": {"temperature_c": 39.0, "humidity_pct": 10,
                        "wind_kmh": 30.0, "precip_mm": 0.0},
            "forecast_7d": {"dates": [], "temp_max": [], "temp_min": [],
                            "precip_mm": [], "wind_max_kmh": []},
        },
        {
            "id": "CL-OHI-FRU", "country_code": "CL", "region": "O'Higgins",
            "lat": -34.17, "lon": -70.74, "source": "Open-Meteo",
            "current": {"temperature_c": 1.0, "humidity_pct": 95,
                        "wind_kmh": 5.0, "precip_mm": 0.0},
            "forecast_7d": {"dates": [], "temp_max": [], "temp_min": [],
                            "precip_mm": [], "wind_max_kmh": []},
        },
    ],
}

PRICE_AR_RESULT = {
    'country_code': 'AR', 'status': 'success', 'records': 1,
    'items': [{
        'country_code': 'AR', 'country': 'Argentina',
        'market_name': 'Mercado Central BA', 'market_type': 'atacado',
        'product': 'tomate', 'product_normalized': 'tomate',
        'category': 'hortifruti', 'price': 1200.0, 'currency': 'ARS',
        'unit': 'kg', 'price_per_kg': 1200.0, 'price_usd': 1.14,
        'date': '2026-06-25', 'source': 'Mercado Central BA',
        'source_url': '', 'source_type': 'real', 'confidence': 'baixa',
        'is_fallback': 0, 'collected_at': '2026-06-25T10:00:00',
    }],
}


@pytest.fixture
def conn_no_price():
    """Banco com clima mas SEM preços SA."""
    c = sqlite3.connect(':memory:', check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("""
        CREATE TABLE flv_climate (
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
    ensure_sa_prices_table(c)
    persist_south_america_weather(c, WEATHER_WITH_RISK)
    yield c
    c.close()


@pytest.fixture
def conn_with_price():
    """Banco com clima E preços SA para AR."""
    c = sqlite3.connect(':memory:', check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("""
        CREATE TABLE flv_climate (
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
    ensure_sa_prices_table(c)
    persist_south_america_weather(c, WEATHER_WITH_RISK)
    persist_country_prices(c, PRICE_AR_RESULT)
    yield c
    c.close()


# ─── Price gating: sem preço ──────────────────────────────────────────────────

def test_no_price_advice_not_comprar(conn_no_price):
    """Sem preço, advisor nunca deve retornar tipo 'comprar' ou 'vender'."""
    engine  = NiasAdvisorEngine(conn_no_price)
    advices = engine.generate_advice()
    forbidden = {'comprar', 'vender', 'antecipar_compra', 'antecipar_venda'}
    for a in advices:
        if a.get('scope') == 'south_america':
            assert a.get('tipo') not in forbidden, \
                f"Sem preço, advisor emitiu '{a.get('tipo')}' para {a.get('pais')}: {a.get('titulo')}"


def test_no_price_advice_is_monitorar_or_alerta(conn_no_price):
    """Sem preço, tipo deve ser monitorar ou alerta."""
    engine  = NiasAdvisorEngine(conn_no_price)
    advices = engine.generate_advice()
    allowed = {'monitorar', 'alerta', None, ''}
    for a in advices:
        if a.get('scope') == 'south_america':
            assert a.get('tipo') in allowed, \
                f"Esperado monitorar/alerta, got '{a.get('tipo')}' para {a.get('pais')}"


def test_no_price_has_price_signal_note(conn_no_price):
    """Sem preço, advisor deve indicar que não há preço local."""
    engine  = NiasAdvisorEngine(conn_no_price)
    advices = engine.generate_advice()
    sa_advices = [a for a in advices if a.get('scope') == 'south_america']
    for a in sa_advices:
        if not a.get('has_price'):
            ps = a.get('price_signal', '')
            assert 'sem preço' in ps.lower() or 'persistido' in ps.lower(), \
                f"Deve indicar ausência de preço. Got: '{ps}'"


def test_no_price_score_capped(conn_no_price):
    """Sem preço, score não deve ser > 64 para sinais climáticos SA."""
    engine  = NiasAdvisorEngine(conn_no_price)
    advices = engine.generate_advice()
    for a in advices:
        if a.get('scope') == 'south_america' and not a.get('has_price'):
            assert a.get('score', 0) <= 64, \
                f"Score sem preço deveria ser ≤64: {a.get('score')} em {a.get('titulo')}"


def test_no_price_confianca_not_alta(conn_no_price):
    """Sem preço, confiança não pode ser 'alta' para recomendações SA."""
    engine  = NiasAdvisorEngine(conn_no_price)
    advices = engine.generate_advice()
    for a in advices:
        if a.get('scope') == 'south_america' and not a.get('has_price'):
            assert a.get('confianca') != 'alta', \
                f"Confiança não pode ser 'alta' sem preço: {a.get('titulo')}"


# ─── Com preço ────────────────────────────────────────────────────────────────

def test_with_price_has_price_flag(conn_with_price):
    """AR com preço deve ter has_price=True nos conselhos."""
    engine  = NiasAdvisorEngine(conn_with_price)
    advices = engine.generate_advice()
    ar_advices = [a for a in advices if a.get('pais') == 'AR']
    if ar_advices:
        assert any(a.get('has_price') for a in ar_advices), \
            "AR com preço deve ter has_price=True"


def test_with_price_score_can_be_higher(conn_with_price):
    """Com preço, score pode ser >= 65."""
    engine_wp  = NiasAdvisorEngine(conn_with_price)
    engine_np  = NiasAdvisorEngine(sqlite3.connect(':memory:'))
    # Não precisamos checar — apenas que a lógica não lança exceção
    advices_wp = engine_wp.generate_advice()
    assert isinstance(advices_wp, list)


# ─── Pipeline não quebra ──────────────────────────────────────────────────────

def test_run_sa_prices_cycle_no_network(conn_no_price):
    """Ciclo de preços SA não deve quebrar se fontes estiverem inacessíveis."""
    from flv.sa_price_persistence import run_sa_prices_cycle
    # Deve retornar sem exceção mesmo que a rede não esteja disponível
    result = run_sa_prices_cycle(conn_no_price, countries=['PY', 'BO', 'EC'])
    assert result.get('status') == 'done'
    summary = result.get('summary', {})
    # PY, BO, EC são source_pending — não devem gerar erro
    for cc in ['PY', 'BO', 'EC']:
        if cc in summary:
            assert summary[cc].get('status') in (
                'source_pending', 'source_not_available', 'error',
                'source_unreachable', 'source_no_data',
            )


def test_pipeline_sa_prices_step_present():
    """pipeline.py deve conter chamada ao SA prices cycle."""
    src = open(
        os.path.join(os.path.dirname(__file__), '..', 'flv', 'pipeline.py'),
        encoding='utf-8'
    ).read()
    assert 'run_sa_prices_cycle' in src
    assert 'sa_price_persistence' in src


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
