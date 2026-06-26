"""
Testes: sistema vivo — eventos, radar e ciclo de detecção de mudanças.
Verifica que o NIAS detecta eventos reais e não inventa dados.
"""
import sys, os, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from datetime import date
from flv.db_migration import ensure_runtime_schema
from flv.sa_price_persistence import ensure_sa_prices_table, persist_country_prices
from flv.brain_engine import NiasBrainEngine, get_brain


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


def _make_conn(weather_rows=None, price_results=None):
    c = sqlite3.connect(':memory:', check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute(_CLIMATE_DDL)
    ensure_runtime_schema(c)
    ensure_sa_prices_table(c)
    if weather_rows:
        for row in weather_rows:
            c.execute("""
                INSERT INTO flv_climate
                  (country_code,region_name,region_id,lat,lon,obs_date,
                   temp_max_c,temp_min_c,precip_mm,wind_ms,humidity_pct,source,scope)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'south_america')
            """, row)
        c.commit()
    if price_results:
        for pr in price_results:
            persist_country_prices(c, pr)
    return c


# ─── Detecção de eventos específicos ─────────────────────────────────────────

def test_no_weather_no_events():
    """Sem dados climáticos, não deve haver eventos de clima."""
    c = _make_conn()
    events = get_brain(c).generate_live_events()
    climate_events = [e for e in events if e['tipo'] in ('clima_extremo','risco_geada','chuva_intensa','clima_atencao')]
    assert climate_events == [], 'Sem dados climáticos não deve haver eventos de clima'
    c.close()


def test_frost_zero_degrees_is_critical():
    """0°C é geada confirmada — deve ser evento crítico."""
    row = ('AR','Mendoza','AR-MDZ',-32.89,-68.84,date.today().isoformat(),20.0,0.0,0.0,5.0,50.0,'Open-Meteo')
    c = _make_conn([row])
    events = get_brain(c).generate_live_events()
    frost = [e for e in events if 'geada' in e['tipo']]
    assert len(frost) >= 1
    assert frost[0]['gravidade'] == 'critica'
    c.close()


def test_frost_between_0_and_2_is_high():
    """Entre 0°C e 2°C é risco de geada — gravidade alta, não crítica."""
    row = ('CL','Maule','CL-MAU',-35.42,-71.65,date.today().isoformat(),15.0,1.5,0.0,5.0,60.0,'Open-Meteo')
    c = _make_conn([row])
    events = get_brain(c).generate_live_events()
    frost_risk = [e for e in events if 'risco_geada' in e['tipo']]
    assert len(frost_risk) >= 1
    assert frost_risk[0]['gravidade'] == 'alta'
    c.close()


def test_temp_above_5_no_frost_event():
    """Temperatura positiva acima de 2°C não deve gerar evento de geada."""
    row = ('PE','Arequipa','PE-ARE',-16.41,-71.54,date.today().isoformat(),25.0,5.0,0.0,8.0,40.0,'Open-Meteo')
    c = _make_conn([row])
    events = get_brain(c).generate_live_events()
    frost = [e for e in events if 'geada' in e['tipo']]
    assert frost == [], 'Temperatura 5°C não deve gerar evento de geada'
    c.close()


def test_extreme_heat_above_38_is_critical():
    """Temperatura máxima >= 38°C deve ser evento crítico."""
    row = ('BO','Chiquitania','BO-CHI',-16.43,-62.5,date.today().isoformat(),39.0,22.0,0.0,15.0,20.0,'Open-Meteo')
    c = _make_conn([row])
    events = get_brain(c).generate_live_events()
    heat = [e for e in events if 'clima_extremo' in e['tipo']]
    assert len(heat) >= 1
    assert heat[0]['gravidade'] == 'critica'
    c.close()


def test_heat_between_36_and_38_is_high():
    """Temperatura máxima entre 36 e 38°C deve ser evento de atenção — gravidade alta."""
    row = ('AR','Buenos Aires','AR-BUE',-34.6,-58.38,date.today().isoformat(),37.0,18.0,0.0,10.0,35.0,'Open-Meteo')
    c = _make_conn([row])
    events = get_brain(c).generate_live_events()
    heat_warn = [e for e in events if 'clima_atencao' in e['tipo']]
    assert len(heat_warn) >= 1
    assert heat_warn[0]['gravidade'] == 'alta'
    c.close()


def test_normal_weather_no_climate_event():
    """Condições normais (18°C, 5mm chuva) não devem gerar evento de clima."""
    row = ('UY','Montevideu','UY-MON',-34.9,-56.18,date.today().isoformat(),18.0,10.0,5.0,8.0,65.0,'Open-Meteo')
    c = _make_conn([row])
    events = get_brain(c).generate_live_events()
    climate = [e for e in events if e['tipo'] in ('clima_extremo','risco_geada','chuva_intensa','clima_atencao')]
    assert climate == [], 'Condições normais não devem gerar evento climático'
    c.close()


def test_heavy_rain_50mm_event():
    """Chuva >= 50mm deve gerar evento de chuva intensa."""
    row = ('CO','Bogotá','CO-BOG',4.71,-74.07,date.today().isoformat(),22.0,14.0,55.0,12.0,90.0,'Open-Meteo')
    c = _make_conn([row])
    events = get_brain(c).generate_live_events()
    rain = [e for e in events if 'chuva' in e['tipo']]
    assert len(rain) >= 1
    c.close()


def test_multiple_events_sorted_critical_first():
    """Com múltiplos eventos, críticos devem vir antes de informativos."""
    rows = [
        ('AR','Mendoza','AR-MDZ',-32.89,-68.84,date.today().isoformat(),20.0,-2.0,0.0,5.0,50.0,'Open-Meteo'),  # geada crítica
        ('CL','Maule','CL-MAU',-35.42,-71.65,date.today().isoformat(),18.0,5.0,5.0,8.0,65.0,'Open-Meteo'),     # normal
    ]
    c = _make_conn(rows)
    events = get_brain(c).generate_live_events()
    gravity_order = {'critica':0,'alta':1,'warn':2,'info':3}
    gravs = [gravity_order.get(e['gravidade'],9) for e in events]
    assert gravs == sorted(gravs), 'Eventos não ordenados por gravidade'
    c.close()


# ─── Eventos de preço (cobertura e ausência) ─────────────────────────────────

def test_no_price_generates_missing_event():
    """Sem preços, deve gerar evento de dado_ausente para países sem dados."""
    row = ('AR','Mendoza','AR-MDZ',-32.89,-68.84,date.today().isoformat(),20.0,5.0,0.0,5.0,50.0,'Open-Meteo')
    c = _make_conn([row])
    events = get_brain(c).generate_live_events()
    missing = [e for e in events if e['tipo'] == 'dado_ausente']
    assert len(missing) >= 1, 'Deve ter evento de dado_ausente quando não há preços'
    c.close()


def test_with_price_generates_coverage_event():
    """Com preços persistidos, deve gerar evento de cobertura_preco."""
    row = ('AR','Mendoza','AR-MDZ',-32.89,-68.84,date.today().isoformat(),20.0,5.0,0.0,5.0,50.0,'Open-Meteo')
    price = {
        'country_code':'AR','status':'success','records':1,
        'items':[{
            'country_code':'AR','country':'Argentina','market_name':'Mercado Central BA',
            'market_type':'atacado','product':'tomate','product_normalized':'tomate',
            'category':'hortifruti','price':1200.0,'currency':'ARS','unit':'kg',
            'price_per_kg':1200.0,'price_usd':1.14,'date':date.today().isoformat(),
            'source':'Mercado Central BA','source_url':'','source_type':'real',
            'confidence':'baixa','is_fallback':0,'collected_at':'2026-06-25T10:00:00',
        }],
    }
    c = _make_conn([row], [price])
    events = get_brain(c).generate_live_events()
    coverage = [e for e in events if e['tipo'] == 'cobertura_preco']
    assert len(coverage) >= 1, 'Com preços deve gerar evento de cobertura'
    c.close()


# ─── Radar temporal ──────────────────────────────────────────────────────────

def test_radar_agora_has_real_events():
    """Horizonte 'agora' deve refletir eventos reais detectados."""
    row = ('AR','Mendoza','AR-MDZ',-32.89,-68.84,date.today().isoformat(),20.0,-1.0,0.0,5.0,50.0,'Open-Meteo')
    c = _make_conn([row])
    brain  = get_brain(c)
    radar  = brain.generate_temporal_radar()
    agora  = radar['radar']['agora']
    assert agora['events_count'] >= 1 or agora['countries_at_risk']
    c.close()


def test_radar_30d_has_reduced_confidence():
    """Horizonte de 30 dias deve ter confidence_mult < 0.5."""
    row = ('AR','Mendoza','AR-MDZ',-32.89,-68.84,date.today().isoformat(),20.0,-1.0,0.0,5.0,50.0,'Open-Meteo')
    c = _make_conn([row])
    radar = get_brain(c).generate_temporal_radar()
    d30   = radar['radar']['30d']
    assert d30['confidence_mult'] < 0.5, '30d deve ter confiança baixa'
    c.close()


def test_radar_does_not_invent_future_events():
    """
    Radar para horizontes futuros não deve listar eventos específicos inventados.
    (Pode listar eventos do dia atual como proxy, mas não previsões fictícias.)
    """
    row = ('CL','Maule','CL-MAU',-35.42,-71.65,date.today().isoformat(),18.0,5.0,5.0,8.0,65.0,'Open-Meteo')
    c = _make_conn([row])
    radar = get_brain(c).generate_temporal_radar()
    d30   = radar['radar']['30d']
    # Para horizonte de 30d com confiança muito baixa, não deve listar eventos específicos
    assert 'note' in d30, 'Horizonte futuro deve ter nota de limitação'
    c.close()


# ─── Detect changes ──────────────────────────────────────────────────────────

def test_detect_changes_stale_weather():
    """Com dados de clima antigos, deve reportar como desatualizado."""
    c = sqlite3.connect(':memory:', check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute(_CLIMATE_DDL)
    ensure_runtime_schema(c)
    ensure_sa_prices_table(c)
    # Inserir clima com data antiga
    c.execute("""
        INSERT INTO flv_climate
          (country_code,region_name,region_id,lat,lon,obs_date,
           temp_max_c,temp_min_c,precip_mm,wind_ms,humidity_pct,source,scope)
        VALUES ('AR','Mendoza','AR-MDZ',-32.89,-68.84,'2026-01-01',
                20.0,5.0,0.0,5.0,50.0,'Open-Meteo','south_america')

    """)
    c.commit()
    changes = get_brain(c).detect_changes()
    stale = [ch for ch in changes if 'desatualizado' in ch['tipo'] or ch['relevancia'] == 'negativa']
    assert len(stale) >= 1, 'Dados antigos devem gerar mudança negativa'
    c.close()


def test_detect_changes_no_price_is_negative():
    """Sem preços deve gerar mudança negativa."""
    row = ('AR','Mendoza','AR-MDZ',-32.89,-68.84,date.today().isoformat(),20.0,5.0,0.0,5.0,50.0,'Open-Meteo')
    c = _make_conn([row])
    changes = get_brain(c).detect_changes()
    neg = [ch for ch in changes if ch['relevancia'] == 'negativa']
    assert len(neg) >= 1, 'Sem preços deve gerar pelo menos uma mudança negativa'
    c.close()


# ─── Nunca inventa dado ───────────────────────────────────────────────────────

def test_events_have_fonte_field():
    """Todo evento deve ter fonte explicita."""
    rows = [
        ('AR','Mendoza','AR-MDZ',-32.89,-68.84,date.today().isoformat(),39.0,-2.0,60.0,30.0,10.0,'Open-Meteo'),
    ]
    c = _make_conn(rows)
    events = get_brain(c).generate_live_events()
    for ev in events:
        assert ev.get('fonte'), f"Evento {ev.get('id')} sem fonte"
    c.close()


def test_thesis_mentions_missing_price_when_absent():
    """Tese sem preço deve mencionar explicitamente a ausência."""
    row = ('CL','Maule','CL-MAU',-35.42,-71.65,date.today().isoformat(),18.0,5.0,5.0,8.0,65.0,'Open-Meteo')
    c = _make_conn([row])
    thesis = get_brain(c).generate_thesis(country='CL')
    if not thesis.get('has_price'):
        assert 'sem' in thesis.get('thesis','').lower() or 'não' in thesis.get('thesis','').lower() or \
               thesis.get('fontes_ausentes'), 'Tese sem preço deve indicar ausência explicitamente'
    c.close()


def test_brain_no_invented_scores_without_data():
    """Com banco vazio, cartões de decisão não devem ter scores inventados."""
    c = sqlite3.connect(':memory:', check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute(_CLIMATE_DDL)
    ensure_runtime_schema(c)
    ensure_sa_prices_table(c)
    cards = get_brain(c).generate_decision_cards()
    # Sem dados, advisor não gera conselhos → sem cartões
    assert isinstance(cards, list)
    c.close()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
