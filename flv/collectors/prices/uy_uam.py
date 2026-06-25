"""
Coletor de preços — Uruguai.
Fonte: Mercado Modelo / UAM (Unidad Administradora del Mercado Modelo).
Dados em UYU (peso uruguaio), referência de atacado hortifrutícola.
"""
from __future__ import annotations

import logging
import re
import urllib.request
from datetime import datetime, date

logger = logging.getLogger(__name__)

_SOURCE_NAME = 'Mercado Modelo (UAM)'
_SOURCE_URL  = 'https://www.mercadomodelo.net/precios'
_COUNTRY     = 'Uruguai'
_CC          = 'UY'
_CURRENCY    = 'UYU'
_TIMEOUT     = 20

PRODUCT_MAP = {
    'tomate':     'tomate', 'tomate perita': 'tomate',
    'cebolla':    'cebola',
    'papa':       'batata',
    'ajo':        'alho',
    'naranja':    'laranja',
    'mandarina':  'mandarina',
    'limon':      'limao',
    'manzana':    'maca',
    'pera':       'pera',
    'lechuga':    'folhosas',
    'zanahoria':  'cenoura',
    'pimiento':   'pimentao',
}


def fetch() -> dict:
    from flv.price_normalizer import normalize_product_name, convert_to_usd, calculate_price_per_kg

    try:
        headers = {'User-Agent': 'NIAS-Research-Bot/1.0'}
        req = urllib.request.Request(_SOURCE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning('[UY-Prices] Mercado Modelo inacessível: %s', e)
        return {
            'country_code': _CC,
            'status':       'source_unreachable',
            'message':      f'Mercado Modelo UY inacessível: {e}',
            'records':      0,
            'source':       _SOURCE_NAME,
            'collected_at': datetime.now().isoformat(),
        }

    items = _parse_html(html)
    if not items:
        return {
            'country_code': _CC,
            'status':       'source_no_data',
            'message':      'Mercado Modelo acessado sem dados parseáveis.',
            'records':      0,
            'source':       _SOURCE_NAME,
            'source_url':   _SOURCE_URL,
            'collected_at': datetime.now().isoformat(),
        }

    today   = date.today().isoformat()
    records = []
    for item in items:
        price_kg  = calculate_price_per_kg(item['price'], item.get('unit', 'kg'))
        price_usd, conf_usd = convert_to_usd(price_kg or item['price'], _CURRENCY)

        records.append({
            'country_code':       _CC,
            'country':            _COUNTRY,
            'market_name':        _SOURCE_NAME,
            'market_type':        'atacado',
            'product':            item['product'],
            'product_normalized': PRODUCT_MAP.get(item['product'].lower(),
                                                   normalize_product_name(item['product'])),
            'category':           'hortifruti',
            'price':              item['price'],
            'currency':           _CURRENCY,
            'unit':               item.get('unit', 'kg'),
            'price_per_kg':       price_kg,
            'price_usd':          price_usd,
            'date':               today,
            'source':             _SOURCE_NAME,
            'source_url':         _SOURCE_URL,
            'source_type':        'real',
            'confidence':         conf_usd if price_usd else 'media',
            'is_fallback':        0,
            'collected_at':       datetime.now().isoformat(),
        })

    return {
        'country_code': _CC,
        'status':       'success',
        'records':      len(records),
        'items':        records,
        'source':       _SOURCE_NAME,
        'source_url':   _SOURCE_URL,
        'currency':     _CURRENCY,
        'collected_at': datetime.now().isoformat(),
    }


def _parse_html(html: str) -> list[dict]:
    items = []
    for prod_name in PRODUCT_MAP:
        pattern = re.compile(
            rf'\b{re.escape(prod_name)}\b.*?(\d{{2,5}}(?:[.,]\d{{1,2}})?)',
            re.IGNORECASE | re.DOTALL
        )
        for match in pattern.findall(html)[:1]:
            try:
                price = float(match.replace('.', '').replace(',', '.'))
                if 1 <= price <= 2000:  # sanidade UYU/kg
                    items.append({'product': prod_name, 'price': price, 'unit': 'kg'})
            except ValueError:
                continue
    return items
