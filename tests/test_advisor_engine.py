"""
Testes: NiasAdvisorEngine — motor de conselho agrocomercial.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.db_migration import ensure_runtime_schema
from flv.advisor_engine import NiasAdvisorEngine, get_advisor


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
            "id": "CL-OHI-FRU", "country_code": "CL", "region": "O'Higgins / Maule",
            "lat": -34.17, "lon": -70.74, "source": "Open-Meteo",
            "current": {"temperature_c": 3.0, "humidity_pct": 90,
                        "wind_kmh": 5.0, "precip_mm": 50.0},
            "forecast_7d": {"dates": [], "temp_max": [], "temp_min": [],
                            "precip_mm": [], "wind_max_kmh": []},
        },
        {
            "id": "BR-SP-CIN", "country_code": "BR", "region": "Cinturão Verde SP",
            "lat": -23.52, "lon": -46.19, "source": "Open-Meteo",
            "current": {"temperature_c": 22.0, "humidity_pct": 65,
                        "wind_kmh": 10.0, "precip_mm": 2.0},
            "forecast_7d": {"dates": [], "temp_max": [], "temp_min": [],
                            "precip_mm": [], "wind_max_kmh": []},
        },
    ],
}


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:", check_same_thread=False)
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
    # Seed weather
    from flv.sa_weather_persistence import persist_south_america_weather
    persist_south_america_weather(c, SAMPLE_WEATHER)
    yield c
    c.close()


def test_advisor_generates_advice(conn):
    engine = get_advisor(conn)
    advices = engine.generate_advice()
    assert isinstance(advices, list)
    assert len(advices) >= 1, "Deve gerar ao menos 1 conselho com dados de clima"


def test_every_advice_has_justificativa(conn):
    engine = get_advisor(conn)
    advices = engine.generate_advice()
    for a in advices:
        assert a.get('justificativa'), f"Conselho sem justificativa: {a.get('titulo')}"


def test_every_advice_has_cenario_contrario(conn):
    engine = get_advisor(conn)
    advices = engine.generate_advice()
    for a in advices:
        assert a.get('cenario_contrario'), f"Conselho sem cenário contrário: {a.get('titulo')}"


def test_every_advice_has_fontes(conn):
    engine = get_advisor(conn)
    advices = engine.generate_advice()
    for a in advices:
        assert a.get('fontes'), f"Conselho sem fontes: {a.get('titulo')}"


def test_every_advice_has_confianca(conn):
    engine = get_advisor(conn)
    advices = engine.generate_advice()
    for a in advices:
        assert a.get('confianca') in ('baixa', 'media', 'alta'), \
            f"Confiança inválida em: {a.get('titulo')}"


def test_every_advice_has_risco(conn):
    engine = get_advisor(conn)
    advices = engine.generate_advice()
    for a in advices:
        assert a.get('risco') in ('baixo', 'medio', 'alto', 'critico'), \
            f"Risco inválido em: {a.get('titulo')}"


def test_every_advice_has_score(conn):
    engine = get_advisor(conn)
    advices = engine.generate_advice()
    for a in advices:
        score = a.get('score')
        assert isinstance(score, (int, float)) and 0 <= score <= 100, \
            f"Score inválido ({score}) em: {a.get('titulo')}"


def test_every_advice_has_acao_recomendada(conn):
    engine = get_advisor(conn)
    advices = engine.generate_advice()
    for a in advices:
        assert a.get('acao_recomendada'), f"Sem ação recomendada em: {a.get('titulo')}"


def test_geada_cl_detected(conn):
    """Chile com chuva intensa deve gerar conselho."""
    engine  = get_advisor(conn)
    advices = engine.generate_advice()
    cl_advice = [a for a in advices if a.get('pais') == 'CL']
    assert cl_advice, "Chile com 50mm de chuva deve gerar conselho"


def test_calor_extremo_ar_detected(conn):
    """Argentina com 38°C deve gerar sinal de calor extremo."""
    engine  = get_advisor(conn)
    advices = engine.generate_advice()
    ar_advice = [a for a in advices if a.get('pais') == 'AR']
    assert ar_advice, "Argentina com 38°C deve gerar conselho"
    assert any('calor extremo' in a.get('sinais_climaticos', []) for a in ar_advice)


def test_br_normal_no_advice(conn):
    """Brasil com condições normais (22°C, 2mm) não deve gerar conselho climático."""
    engine  = get_advisor(conn)
    advices = engine.generate_advice()
    br_climate = [a for a in advices
                  if a.get('pais') == 'BR' and a.get('scope') == 'south_america']
    assert not br_climate, "BR sem evento climático extremo não deve gerar alerta climático"


def test_score_calc(conn):
    engine = get_advisor(conn)
    score_obj = engine.calculate_risk_return_score({
        'signals':          ['risco de geada'],
        'weather':          True,
        'price':            False,
        'days_old_weather': 0,
        'days_old_price':   999,
        'has_geada':        True,
    })
    assert score_obj['score'] > 0
    assert score_obj['risco'] == 'alto'


def test_contrarian_scenario_not_empty(conn):
    engine = get_advisor(conn)
    c = engine.generate_contrarian_scenario({
        'signals': ['risco de geada'],
        'product': 'uva',
        'country': 'CL',
        'region':  'O\'Higgins',
    })
    assert len(c) > 30, "Cenário contrário deve ser texto substantivo"


def test_explain_recommendation_is_prose(conn):
    engine = get_advisor(conn)
    a = engine.generate_advice()[0]
    text = engine.explain_recommendation(a)
    assert len(text) > 50, "Explicação deve ser texto de pelo menos 50 chars"
    # Não deve ser só número
    assert not text.strip().replace('.', '').replace('%', '').isdigit()


def test_executive_summary_has_resumo(conn):
    engine  = get_advisor(conn)
    summary = engine.generate_executive_summary()
    assert summary.get('resumo'), "Resumo executivo deve ter texto"
    assert summary.get('total_conselhos') is not None
    assert summary.get('scope') == 'south_america'


def test_rank_opportunities_subset_of_advice(conn):
    engine = get_advisor(conn)
    all_advice = engine.generate_advice()
    opps       = engine.rank_opportunities()
    assert all(a in all_advice for a in opps), \
        "rank_opportunities deve ser subconjunto de generate_advice"
    assert all(a.get('score', 0) >= 55 for a in opps)


def test_build_thesis_missing_data(conn):
    engine = get_advisor(conn)
    thesis = engine.build_investment_thesis(product='mandioca_xpto_inexistente', region='regiao_inexistente')
    assert thesis.get('status') == 'insuficiente'
    assert 'mensagem' in thesis


def test_no_invented_price_signal(conn):
    """O advisor não deve inventar sinal de preço quando não há dado."""
    engine  = get_advisor(conn)
    advices = engine.generate_advice()
    for a in advices:
        if a.get('scope') == 'south_america':
            assert a.get('price_signal') != 'alta confirmada' and \
                   a.get('price_signal') != 'queda confirmada', \
                f"Advisor inventou preço para {a.get('pais')}: {a.get('price_signal')}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
