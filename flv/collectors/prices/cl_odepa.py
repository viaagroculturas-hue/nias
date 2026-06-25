"""
Coletor de preços — Chile.
Fonte: ODEPA — Oficina de Estudios y Políticas Agrarias.

ODEPA é a fonte oficial mais estruturada da América do Sul para preços agrícolas.
Publicações em https://www.odepa.gob.cl/estadisticas-del-sector/estadisticas-productivas/informacion-de-precios
Dados em CLP (peso chileno).
"""
from __future__ import annotations

import json
import logging
import re
import urllib.request
from datetime import datetime, date

logger = logging.getLogger(__name__)

_SOURCE_NAME = 'ODEPA'
_SOURCE_URL  = 'https://www.odepa.gob.cl/estadisticas-del-sector/estadisticas-productivas/informacion-de-precios'
_API_BASE    = 'https://api.odepa.gob.cl'
_COUNTRY     = 'Chile'
_CC          = 'CL'
_CURRENCY    = 'CLP'
_TIMEOUT     = 25

PRODUCT_MAP = {
    'tomate':    'tomate',
    'cebolla':   'cebola',
    'papa':      'batata',
    'ajo':       'alho',
    'zanahoria': 'cenoura',
    'pimiento':  'pimentao',
    'lechuga':   'folhosas',
    'manzana':   'maca',
    'pera':      'pera',
    'uva':       'uva',
    'naranja':   'laranja',
    'limon':     'limao',
    'limon sutil': 'limao',
    'palto':     'abacate',
    'aguacate':  'abacate',
}


def fetch() -> dict:
    """Busca preços da ODEPA. Tenta API JSON; fallback para página HTML."""
    from flv.price_normalizer import normalize_product_name, convert_to_usd, calculate_price_per_kg

    items = _try_api()
    if not items:
        items = _try_html()

    if not items:
        return {
            'country_code': _CC,
            'status':       'source_no_data',
            'message':      'ODEPA acessada mas sem dados estruturados disponíveis no momento.',
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
    """Tenta endpoint JSON da API ODEPA."""
    today = date.today().isoformat()
    try:
        headers = {
            'User-Agent': 'NIAS-Research-Bot/1.0',
            'Accept': 'application/json',
        }
        # ODEPA API endpoint (verificado como público)
        url = f'{_API_BASE}/precios?fecha={today}&formato=json'
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode('utf-8', errors='ignore'))

        items = []
        # Estrutura esperada: lista de registros com produto, precio, unidad, fecha
        rows = data if isinstance(data, list) else data.get('data', data.get('precios', []))
        for row in rows:
            prod = (row.get('producto') or row.get('especie') or '').lower().strip()
            price_val = row.get('precio_promedio') or row.get('precio') or row.get('price')
            unit = row.get('unidad') or row.get('unit', 'kg')
            fecha = row.get('fecha') or row.get('date', today)
            if prod and price_val:
                try:
                    items.append({'product': prod, 'price': float(price_val), 'unit': unit, 'date': fecha[:10]})
                except (ValueError, TypeError):
                    pass
        return items
    except Exception as e:
        logger.debug('[CL-ODEPA] API falhou: %s', e)
        return []


def _try_html() -> list[dict]:
    """Fallback: parse de tabela HTML da página ODEPA."""
    today = date.today().isoformat()
    try:
        headers = {'User-Agent': 'NIAS-Research-Bot/1.0'}
        req = urllib.request.Request(_SOURCE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.debug('[CL-ODEPA] HTML fallback falhou: %s', e)
        return []

    items = []
    for prod_name in PRODUCT_MAP:
        pattern = re.compile(
            rf'\b{re.escape(prod_name)}\b.*?(\d{{3,6}}(?:[.,]\d{{1,2}})?)',
            re.IGNORECASE | re.DOTALL
        )
        matches = pattern.findall(html)
        for match in matches[:1]:
            try:
                price = float(match.replace('.', '').replace(',', '.'))
                if 10 <= price <= 10_000_000:  # sanidade CLP
                    items.append({'product': prod_name, 'price': price, 'unit': 'kg', 'date': today})
            except ValueError:
                continue
    return items
