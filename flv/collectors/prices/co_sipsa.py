"""
Coletor de preços — Colômbia.
Fonte: SIPSA / DANE — Sistema de Información de Precios del Sector Agropecuario.
URL: https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa

DANE publica boletins semanais em CSV/Excel e API pública.
Dados em COP (peso colombiano).
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from datetime import datetime, date

logger = logging.getLogger(__name__)

_SOURCE_NAME = 'SIPSA/DANE'
_SOURCE_URL  = 'https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa'
_COUNTRY     = 'Colômbia'
_CC          = 'CO'
_CURRENCY    = 'COP'
_TIMEOUT     = 25

# API DANE SIPSA (endpoint público documentado)
_SIPSA_API   = 'https://sitios.dane.gov.co/sipsa-exportar/archivos/semanas'

PRODUCT_MAP = {
    'tomate':     'tomate', 'tomate chonto': 'tomate', 'tomate larga vida': 'tomate',
    'cebolla':    'cebola', 'cebolla cabezona': 'cebola',
    'papa':       'batata', 'papa pastusa': 'batata', 'papa criolla': 'batata',
    'platano':    'banana', 'plátano': 'banana',
    'aguacate':   'abacate',
    'mango':      'manga',
    'naranja':    'laranja',
    'zanahoria':  'cenoura',
    'lechuga':    'folhosas',
    'pimentón':   'pimentao', 'pimenton': 'pimentao',
    'ajo':        'alho',
}


def fetch() -> dict:
    from flv.price_normalizer import normalize_product_name, convert_to_usd, calculate_price_per_kg

    items = _try_api()
    if not items:
        items = _try_html()

    if not items:
        return {
            'country_code': _CC,
            'status':       'source_no_data',
            'message':      'SIPSA/DANE acessado mas sem dados estruturados disponíveis.',
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
            'market_name':        'Corabastos/SIPSA',
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
            'date':               item.get('date', today),
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


def _try_api() -> list[dict]:
    """Tenta API pública DANE SIPSA."""
    try:
        headers = {
            'User-Agent': 'NIAS-Research-Bot/1.0',
            'Accept': 'application/json',
        }
        req = urllib.request.Request(_SIPSA_API, headers=headers)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read())

        items = []
        rows = data if isinstance(data, list) else data.get('data', [])
        today = date.today().isoformat()
        for row in rows:
            prod = (row.get('producto') or row.get('nombre') or '').lower().strip()
            price_val = row.get('precio') or row.get('precio_promedio')
            unit = row.get('unidad', 'kg')
            fecha = (row.get('fecha') or today)[:10]
            if prod and price_val:
                try:
                    items.append({'product': prod, 'price': float(price_val), 'unit': unit, 'date': fecha})
                except (ValueError, TypeError):
                    pass
        return items
    except Exception as e:
        logger.debug('[CO-SIPSA] API falhou: %s', e)
        return []


def _try_html() -> list[dict]:
    """Fallback: parse HTML da página SIPSA."""
    today = date.today().isoformat()
    try:
        headers = {'User-Agent': 'NIAS-Research-Bot/1.0'}
        req = urllib.request.Request(_SOURCE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.debug('[CO-SIPSA] HTML falhou: %s', e)
        return []

    items = []
    for prod_name in PRODUCT_MAP:
        pattern = re.compile(
            rf'\b{re.escape(prod_name)}\b.*?(\d{{4,7}}(?:[.,]\d{{1,2}})?)',
            re.IGNORECASE | re.DOTALL
        )
        for match in pattern.findall(html)[:1]:
            try:
                price = float(match.replace('.', '').replace(',', '.'))
                if 100 <= price <= 50_000_000:  # sanidade COP/kg
                    items.append({'product': prod_name, 'price': price, 'unit': 'kg', 'date': today})
            except ValueError:
                continue
    return items
