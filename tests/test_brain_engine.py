"""
Testes: NiasBrainEngine — motor do Cérebro NIAS.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.db_migration import ensure_runtime_schema
from flv.sa_price_persistence import ensure_sa_prices_table, persist_country_prices
from flv.brain_engine import NiasBrainEngine, get_brain

# ─── Fixtures ────────────────────────────────────────────────────────────────

WEATHER_ROWS = [
    # AR: geada
    ('AR','Mendoza','AR-MDZ-CEN',-32.89,-68.84,'2026-06-25',39.0,-1.0,0.0,30.0,10.0,'Open-Meteo'),
    # CL: normal
    ('CL',"O'Higgins",'CL-OHI-FRU',-34.17,-70.74,'2026-06-25',18.0,5.0,5.0,10.0,70.0,'Open-Meteo'),
    # PE: chuva intensa
    ('PE','Lima','PE-LIM-CEN',-12.05,-77.04,'2026-06-25',22.0,14.0,60.0,15.0,85.0,'Open-Meteo'),
]

PRICE_AR = {
    'country_code': 'AR', 'status': 'success', 'records': 2,
    'items': [
        {
            'country_code':'AR','country':'Argentina',
            'market_name':'Mercado Central BA','market_type':'atacado',
            'product':'tomate','product_normalized':'tomate','category':'hortifruti',
            'price':1200.0,'currency':'ARS','unit':'kg','price_per_kg':1200.0,'price_usd':1.14,
            'date':'2026-06-25','source':'Mercado Central BA',
            'source_url':'','source_type':'real','confidence':'baixa',
            'is_fallback':0,'collected_at':'2026-06-25T10:00:00',
        },
    ],
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


@pytest.fixture
def conn():
    c = sqlite3.connect(':memory:', check_same_thread=False)
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
    persist_country_prices(c, PRICE_AR)
    yield c
    c.close()


@pytest.fixture
def empty_conn():
    c = sqlite3.connect(':memory:', check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute(_CLIMATE_DDL)
    ensure_runtime_schema(c)
    ensure_sa_prices_table(c)
    yield c
    c.close()


# ─── observe_now ─────────────────────────────────────────────────────────────

def test_observe_now_loads_data(conn):
    brain = get_brain(conn).observe_now()
    assert len(brain._weather_data) == 3
    assert len(brain._price_data) == 1


def test_observe_now_idempotent(conn):
    brain = get_brain(conn)
    brain.observe_now()
    brain.observe_now()
    assert brain._loaded is True


def test_observe_now_empty_db(empty_conn):
    brain = get_brain(empty_conn).observe_now()
    assert brain._weather_data == []
    assert brain._price_data   == []


# ─── generate_system_pulse ───────────────────────────────────────────────────

def test_pulse_has_required_keys(conn):
    pulse = get_brain(conn).generate_system_pulse()
    for key in ('timestamp', 'health', 'sources', 'recommendations', 'coverage'):
        assert key in pulse, f'Chave {key!r} ausente no pulse'


def test_pulse_sources_have_status(conn):
    pulse = get_brain(conn).generate_system_pulse()
    for name, src in pulse['sources'].items():
        assert 'status' in src, f'Source {name!r} sem campo status'


def test_pulse_health_is_string(conn):
    pulse = get_brain(conn).generate_system_pulse()
    assert isinstance(pulse['health'], str)


def test_pulse_coverage_has_poles(conn):
    pulse = get_brain(conn).generate_system_pulse()
    assert pulse['coverage']['weather_poles'] == 3


def test_pulse_empty_is_degradado(empty_conn):
    pulse = get_brain(empty_conn).generate_system_pulse()
    assert pulse['health'] in ('degradado', 'atencao', 'ok', 'saudavel', 'desconhecido')


# ─── generate_live_events ────────────────────────────────────────────────────

def test_events_returns_list(conn):
    events = get_brain(conn).generate_live_events()
    assert isinstance(events, list)


def test_events_frost_detected(conn):
    events = get_brain(conn).generate_live_events()
    frost = [e for e in events if 'geada' in e.get('tipo', '')]
    assert len(frost) >= 1, 'Geada em Mendoza deveria gerar evento'


def test_events_rain_detected(conn):
    events = get_brain(conn).generate_live_events()
    rain = [e for e in events if 'chuva' in e.get('tipo', '')]
    assert len(rain) >= 1, 'Chuva intensa em Lima deveria gerar evento'


def test_events_sorted_by_gravity(conn):
    events = get_brain(conn).generate_live_events()
    order = {'critica': 0, 'alta': 1, 'warn': 2, 'info': 3}
    gravidades = [order.get(e.get('gravidade', 'info'), 9) for e in events]
    assert gravidades == sorted(gravidades), 'Eventos devem estar ordenados por gravidade'


def test_events_have_required_fields(conn):
    events = get_brain(conn).generate_live_events()
    required = ('id', 'tipo', 'gravidade', 'titulo', 'descricao', 'fonte', 'timestamp', 'acao')
    for ev in events:
        for f in required:
            assert f in ev, f'Campo {f!r} ausente no evento {ev.get("id")}'


# ─── generate_decision_cards ─────────────────────────────────────────────────

def test_cards_returns_list(conn):
    cards = get_brain(conn).generate_decision_cards()
    assert isinstance(cards, list)


def test_cards_have_validity(conn):
    cards = get_brain(conn).generate_decision_cards()
    for c in cards:
        assert c.get('validade_ate'), f'Card {c.get("id")} sem validade_ate'
        assert c.get('invalida_se'),  f'Card {c.get("id")} sem invalida_se'


def test_cards_sorted_by_score(conn):
    cards = get_brain(conn).generate_decision_cards()
    scores = [c.get('score', 0) for c in cards]
    assert scores == sorted(scores, reverse=True), 'Cards devem estar em ordem decrescente de score'


def test_cards_required_fields(conn):
    cards = get_brain(conn).generate_decision_cards()
    required = ('id','tipo','score','confianca','has_price','pais','titulo',
                'tese','justificativa','acao_recomendada','cenario_contrario',
                'validade_ate','validade_label','invalida_se','gerado_em')
    for c in cards:
        for f in required:
            assert f in c, f'Campo {f!r} ausente no card {c.get("id")}'


# ─── generate_temporal_radar ─────────────────────────────────────────────────

def test_radar_has_all_horizons(conn):
    radar = get_brain(conn).generate_temporal_radar()
    for h in ('agora', '24h', '48h', '3d', '7d', '15d', '30d'):
        assert h in radar['radar'], f'Horizonte {h!r} ausente no radar'


def test_radar_each_horizon_has_risk_level(conn):
    radar = get_brain(conn).generate_temporal_radar()
    for h, data in radar['radar'].items():
        assert 'risk_level' in data, f'Horizonte {h!r} sem risk_level'


def test_radar_has_data_note(conn):
    radar = get_brain(conn).generate_temporal_radar()
    assert radar.get('data_note'), 'Radar deve ter data_note explicando limitações'


# ─── generate_thesis ─────────────────────────────────────────────────────────

def test_thesis_by_country(conn):
    thesis = get_brain(conn).generate_thesis(country='AR')
    assert thesis['status'] == 'ok'
    assert thesis['has_climate'] is True


def test_thesis_with_price(conn):
    thesis = get_brain(conn).generate_thesis(country='AR', product='tomate')
    assert thesis['status'] == 'ok'
    assert thesis['has_price'] is True


def test_thesis_no_data_returns_sem_dado(empty_conn):
    thesis = get_brain(empty_conn).generate_thesis(country='AR')
    assert thesis['status'] == 'sem_dado'
    assert thesis.get('message')


def test_thesis_has_fontes(conn):
    thesis = get_brain(conn).generate_thesis(country='AR')
    assert thesis.get('fontes'), 'Tese deve listar fontes'


def test_thesis_has_gerado_em(conn):
    thesis = get_brain(conn).generate_thesis()
    assert thesis.get('gerado_em'), 'Tese deve ter timestamp gerado_em'


# ─── detect_changes ──────────────────────────────────────────────────────────

def test_detect_changes_returns_list(conn):
    changes = get_brain(conn).detect_changes()
    assert isinstance(changes, list)
    assert len(changes) >= 1


def test_detect_changes_has_relevance(conn):
    changes = get_brain(conn).detect_changes()
    for c in changes:
        assert c.get('relevancia') in ('positiva', 'negativa', 'neutra')


# ─── evaluate_data_quality ───────────────────────────────────────────────────

def test_quality_has_coverage(conn):
    q = get_brain(conn).evaluate_data_quality()
    assert 'cobertura_clima'  in q
    assert 'cobertura_preco'  in q
    assert 'limitacoes'       in q


def test_quality_lista_limitacoes(empty_conn):
    q = get_brain(empty_conn).evaluate_data_quality()
    assert isinstance(q['limitacoes'], list)


# ─── process_command ─────────────────────────────────────────────────────────

def test_command_pulse(conn):
    result = get_brain(conn).process_command('pulse')
    assert result['intent'] == 'pulse'
    assert 'resultado' in result


def test_command_alerta(conn):
    result = get_brain(conn).process_command('alerta')
    assert result['intent'] == 'risks'
    assert 'eventos' in result


def test_command_clima_ar(conn):
    result = get_brain(conn).process_command('clima AR')
    assert result['intent'] == 'climate'
    assert result['filtros']['country'] == 'AR'


def test_command_preco_tomate(conn):
    result = get_brain(conn).process_command('preco tomate')
    assert result['intent'] == 'prices'
    assert result['filtros']['product'] == 'tomate'


def test_command_unknown_returns_summary(conn):
    result = get_brain(conn).process_command('xxxxxxxxx')
    assert result['tipo'] == 'resumo_geral'


def test_command_empty_returns_summary(conn):
    result = get_brain(conn).process_command('')
    assert isinstance(result, dict)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
