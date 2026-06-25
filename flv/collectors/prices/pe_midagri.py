"""
Coletor de preços — Peru.
Fonte: MIDAGRI / SISAP — Sistema de Información de Abastecimiento y Precios.
URL: https://sistemas.midagri.gob.pe/sisap/portal2/mayorista/

Dados em PEN (sol peruano), mercados mayoristas de Lima.
"""
from __future__ import annotations

import logging
import re
import urllib.request
from datetime import datetime, date

logger = logging.getLogger(__name__)

_SOURCE_NAME = 'MIDAGRI/SISAP'
_SOURCE_URL  = 'https://sistemas.midagri.gob.pe/sisap/portal2/mayorista/'
_COUNTRY     = 'Peru'
_CC          = 'PE'
_CURRENCY    = 'PEN'
_TIMEOUT     = 25

PRODUCT_MAP = {
    'papa':     'batata', 'papa blanca': 'batata', 'papa amarilla': 'batata',
    'tomate':   'tomate',
    'cebolla':  'cebola', 'cebolla amarilla': 'cebola',
    'ajo':      'alho',
    'limon':    'limao',  'limón': 'limao',
    'naranja':  'laranja',
    'mango':    'manga',
    'platano':  'banana', 'plátano': 'banana',
    'uva':      'uva',
    'zanahoria': 'cenoura',
    'lechuga':  'folhosas',
    'pimiento': 'pimentao',
}


def fetch() -> dict:
    from flv.price_normalizer import normalize_product_name, convert_to_usd, calculate_price_per_kg

    try:
        headers = {
            'User-Agent': 'NIAS-Research-Bot/1.0',
            'Accept': 'text/html,application/xhtml+xml',
        }
        req = urllib.request.Request(_SOURCE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning('[PE-Prices] SISAP inacessível: %s', e)
        return {
            'country_code': _CC,
            'status':       'source_unreachable',
            'message':      f'MIDAGRI/SISAP inacessível: {e}',
            'records':      0,
            'source':       _SOURCE_NAME,
            'collected_at': datetime.now().isoformat(),
        }

    items = _parse_sisap_html(html)
    if not items:
        return {
            'country_code': _CC,
            'status':       'source_no_data',
            'message':      'SISAP acessado mas sem dados parseáveis no momento.',
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
            'market_name':        'Mercado Mayorista Lima',
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


def _parse_sisap_html(html: str) -> list[dict]:
    items = []
    for prod_name in PRODUCT_MAP:
        pattern = re.compile(
            rf'\b{re.escape(prod_name)}\b.*?(\d{{1,3}}(?:[.,]\d{{2,2}})?)',
            re.IGNORECASE | re.DOTALL
        )
        for match in pattern.findall(html)[:1]:
            try:
                price = float(match.replace(',', '.'))
                if 0.1 <= price <= 50:  # sanidade PEN/kg
                    items.append({'product': prod_name, 'price': price, 'unit': 'kg'})
            except ValueError:
                continue
    return items
