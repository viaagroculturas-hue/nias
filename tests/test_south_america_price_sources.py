"""
Testes: mapa de fontes de preço sul-americanas.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.south_america_price_sources import (
    SOUTH_AMERICA_PRICE_SOURCES,
    get_source_config,
    get_all_countries,
    get_implemented_countries,
    get_status_summary,
)

REQUIRED_COUNTRIES = ['BR', 'AR', 'CL', 'PE', 'PY', 'UY', 'CO', 'EC', 'BO']


def test_all_required_countries_present():
    countries = get_all_countries()
    for cc in REQUIRED_COUNTRIES:
        assert cc in countries, f"País {cc} ausente do mapa de fontes"


def test_every_country_has_name():
    for cc, cfg in SOUTH_AMERICA_PRICE_SOURCES.items():
        assert cfg.get('name'), f"{cc}: campo 'name' ausente"


def test_every_country_has_currency():
    for cc, cfg in SOUTH_AMERICA_PRICE_SOURCES.items():
        assert cfg.get('currency'), f"{cc}: campo 'currency' ausente"


def test_every_country_has_status():
    valid_statuses = {'real', 'partial', 'to_research', 'needs_auth', 'unavailable', 'no_source'}
    for cc, cfg in SOUTH_AMERICA_PRICE_SOURCES.items():
        assert cfg.get('status') in valid_statuses, \
            f"{cc}: status inválido '{cfg.get('status')}'"


def test_every_country_has_sources_list():
    for cc, cfg in SOUTH_AMERICA_PRICE_SOURCES.items():
        assert isinstance(cfg.get('sources'), list), f"{cc}: 'sources' deve ser lista"
        assert len(cfg['sources']) >= 1, f"{cc}: deve ter ao menos 1 fonte definida"


def test_every_source_has_required_fields():
    required = ['name', 'url', 'access_type', 'legal_status', 'status']
    for cc, cfg in SOUTH_AMERICA_PRICE_SOURCES.items():
        for src in cfg.get('sources', []):
            for field in required:
                assert field in src, f"{cc}/{src.get('name')}: campo '{field}' ausente"


def test_br_is_real():
    assert SOUTH_AMERICA_PRICE_SOURCES['BR']['status'] == 'real'


def test_br_has_conab():
    br = SOUTH_AMERICA_PRICE_SOURCES['BR']
    names = [s['name'] for s in br['sources']]
    assert any('CONAB' in n for n in names), "Brasil deve ter CONAB como fonte"


def test_br_implemented_true():
    br = SOUTH_AMERICA_PRICE_SOURCES['BR']
    implemented = [s for s in br['sources'] if s.get('implemented')]
    assert implemented, "Brasil deve ter pelo menos 1 fonte implementada"


def test_implemented_countries():
    impl = get_implemented_countries()
    assert 'BR' in impl, "BR deve estar em implemented_countries"
    assert len(impl) >= 2, "Deve haver ao menos 2 países implementados"


def test_get_source_config_returns_dict():
    cfg = get_source_config('AR')
    assert isinstance(cfg, dict)
    assert cfg.get('name') == 'Argentina'


def test_get_source_config_missing_returns_empty():
    cfg = get_source_config('XX')
    assert cfg == {}


def test_status_summary_returns_all_countries():
    summary = get_status_summary()
    for cc in REQUIRED_COUNTRIES:
        assert cc in summary, f"{cc} ausente do status_summary"


def test_status_summary_has_required_fields():
    summary = get_status_summary()
    for cc, info in summary.items():
        assert 'country' in info
        assert 'status' in info
        assert 'currency' in info


def test_ar_has_mercado_central():
    ar = SOUTH_AMERICA_PRICE_SOURCES['AR']
    names = [s['name'] for s in ar['sources']]
    assert any('Mercado Central' in n for n in names)


def test_cl_has_odepa():
    cl = SOUTH_AMERICA_PRICE_SOURCES['CL']
    names = [s['name'] for s in cl['sources']]
    assert any('ODEPA' in n for n in names)


def test_co_has_sipsa():
    co = SOUTH_AMERICA_PRICE_SOURCES['CO']
    names = [s['name'] for s in co['sources']]
    assert any('SIPSA' in n for n in names)


def test_pe_has_midagri():
    pe = SOUTH_AMERICA_PRICE_SOURCES['PE']
    names = [s['name'] for s in pe['sources']]
    assert any('MIDAGRI' in n for n in names)


def test_uy_has_mercado_modelo():
    uy = SOUTH_AMERICA_PRICE_SOURCES['UY']
    names = [s['name'] for s in uy['sources']]
    assert any('Mercado Modelo' in n for n in names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
