"""
Testes: flv/price_normalizer.py — normalização de produtos, moedas e unidades.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from flv.price_normalizer import (
    normalize_product_name,
    normalize_unit,
    normalize_currency,
    calculate_price_per_kg,
    convert_to_usd,
    get_exchange_rate_to_usd,
    standardize_market_name,
    can_compare_regionally,
)


# ─── normalize_product_name ──────────────────────────────────────────────────

def test_tomate_pt():
    assert normalize_product_name('Tomate') == 'tomate'

def test_tomate_carmem():
    assert normalize_product_name('Tomate Carmem') == 'tomate'

def test_papa_to_batata():
    assert normalize_product_name('Papa') == 'batata'

def test_papa_blanca_to_batata():
    assert normalize_product_name('papa blanca') == 'batata'

def test_cebolla_to_cebola():
    assert normalize_product_name('cebolla') == 'cebola'

def test_platano_to_banana():
    assert normalize_product_name('platano') == 'banana'

def test_palto_to_abacate():
    assert normalize_product_name('palto') == 'abacate'

def test_aguacate_to_abacate():
    assert normalize_product_name('aguacate') == 'abacate'

def test_unknown_product_returns_slug():
    result = normalize_product_name('fruta_exotica')
    assert 'fruta' in result or result == 'fruta_exotica'

def test_empty_product():
    assert normalize_product_name('') == ''


# ─── normalize_unit ──────────────────────────────────────────────────────────

def test_kg_unit():
    assert normalize_unit('kg') == 'kg'

def test_kg_caps():
    assert normalize_unit('KG') == 'kg'

def test_kilo_alias():
    assert normalize_unit('kilo') == 'kg'

def test_empty_unit_returns_kg():
    assert normalize_unit('') == 'kg'


# ─── normalize_currency ──────────────────────────────────────────────────────

def test_brl_currency():
    assert normalize_currency('BRL') == 'BRL'

def test_r_dollar_to_brl():
    assert normalize_currency('R$') == 'BRL'

def test_ars_ok():
    assert normalize_currency('ARS') == 'ARS'

def test_soles_to_pen():
    assert normalize_currency('SOLES') == 'PEN'

def test_usd_ok():
    assert normalize_currency('USD') == 'USD'


# ─── calculate_price_per_kg ──────────────────────────────────────────────────

def test_price_per_kg_already_kg():
    result = calculate_price_per_kg(10.0, 'kg')
    assert result == 10.0

def test_price_per_kg_from_ton():
    result = calculate_price_per_kg(10000.0, 't')
    assert abs(result - 10.0) < 0.01

def test_price_per_kg_from_grams():
    result = calculate_price_per_kg(0.01, 'g')
    assert abs(result - 10.0) < 0.01

def test_price_per_kg_unidade_returns_none():
    result = calculate_price_per_kg(5.0, 'unidade')
    assert result is None

def test_price_per_kg_zero_price():
    result = calculate_price_per_kg(0, 'kg')
    assert result is None


# ─── convert_to_usd ──────────────────────────────────────────────────────────

def test_usd_to_usd():
    price, conf = convert_to_usd(1.0, 'USD')
    assert price == 1.0
    assert conf == 'alta'

def test_brl_to_usd():
    price, conf = convert_to_usd(5.40, 'BRL')
    assert price is not None
    assert price > 0
    assert conf in ('baixa', 'media', 'alta')

def test_ars_to_usd():
    price, conf = convert_to_usd(1000.0, 'ARS')
    assert price is not None
    assert price < 10  # 1000 ARS é menos de $10 USD

def test_unknown_currency():
    price, conf = convert_to_usd(10.0, 'XYZ')
    assert price is None or conf == 'sem_dado'

def test_zero_price_returns_none():
    price, conf = convert_to_usd(0, 'BRL')
    assert price is None


# ─── get_exchange_rate_to_usd ────────────────────────────────────────────────

def test_usd_rate_is_1():
    rate, conf = get_exchange_rate_to_usd('USD')
    assert rate == 1.0
    assert conf == 'alta'

def test_brl_has_rate():
    rate, conf = get_exchange_rate_to_usd('BRL')
    assert rate > 0
    assert rate < 1  # R$ é menor que 1 USD

def test_unknown_currency_rate_zero():
    rate, conf = get_exchange_rate_to_usd('XYZ')
    assert rate == 0.0 or conf == 'sem_dado'


# ─── standardize_market_name ─────────────────────────────────────────────────

def test_ceagesp_name():
    result = standardize_market_name('CEAGESP')
    assert 'SP' in result or 'BR' in result

def test_empty_market():
    result = standardize_market_name('', 'AR')
    assert 'AR' in result or result != ''

def test_unknown_market_passes_through():
    result = standardize_market_name('Mercado Municipal XYZ')
    assert 'XYZ' in result


# ─── can_compare_regionally ──────────────────────────────────────────────────

def test_single_country_cannot_compare():
    items = [{'country_code': 'BR', 'currency': 'BRL', 'price_usd': 2.0, 'confidence': 'media'}]
    can, reason = can_compare_regionally(items)
    assert not can

def test_two_countries_with_usd_can_compare():
    items = [
        {'country_code': 'BR', 'currency': 'BRL', 'price_usd': 2.0, 'confidence': 'media'},
        {'country_code': 'AR', 'currency': 'ARS', 'price_usd': 1.5, 'confidence': 'media'},
    ]
    can, reason = can_compare_regionally(items)
    assert can

def test_missing_usd_cannot_compare():
    items = [
        {'country_code': 'BR', 'currency': 'BRL', 'price_usd': 2.0, 'confidence': 'media'},
        {'country_code': 'BO', 'currency': 'BOB', 'price_usd': None, 'confidence': 'sem_dado'},
    ]
    can, reason = can_compare_regionally(items)
    assert not can


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
