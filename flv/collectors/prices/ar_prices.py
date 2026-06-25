"""
Coletor de preços — Argentina.
Fonte: Mercado Central de Buenos Aires (página HTML pública).

O Mercado Central publica boletim HTML diário com tabela de preços.
Este coletor faz parse controlado da tabela sem scraping agressivo.
Respeita timeout, identifica User-Agent como bot de pesquisa acadêmica/pública.
"""
from __future__ import annotations

import logging
import re
import urllib.request
from datetime import datetime, date

logger = logging.getLogger(__name__)

_SOURCE_NAME = 'Mercado Central de Buenos Aires'
_SOURCE_URL  = 'https://www.mercadocentral.gob.ar/paginas/informacion-de-precios'
_COUNTRY     = 'Argentina'
_CC          = 'AR'
_CURRENCY    = 'ARS'
_UNIT        = 'kg'
_TIMEOUT     = 20

# Mapeamento de nomes em espanhol para slug NIAS
PRODUCT_MAP = {
    'tomate':    'tomate', 'tomate redondo': 'tomate', 'tomate perita': 'tomate',
    'cebolla':   'cebola', 'cebolla blanca': 'cebola',
    'papa':      'batata', 'papa blanca': 'batata', 'papa negra': 'batata',
    'ajo':       'alho',   'ajo blanco': 'alho',
    'zanahoria': 'cenoura',
    'pimiento':  'pimentao',
    'manzana':   'maca',   'manzana verde': 'maca', 'manzana roja': 'maca',
    'pera':      'pera',
    'uva':       'uva',    'uva blanca': 'uva', 'uva negra': 'uva',
    'naranja':   'laranja',
    'limon':     'limao',  'limón': 'limao',
    'banana':    'banana', 'platano': 'banana',
    'mandarina': 'mandarina',
    'lechuga':   'folhosas',
}


def fetch() -> dict:
    """
    Busca preços no Mercado Central de Buenos Aires.
    Retorna dict com status e lista de registros.
    """
    from flv.price_normalizer import normalize_product_name, convert_to_usd, calculate_price_per_kg

    try:
        headers = {
            'User-Agent': 'NIAS-Research-Bot/1.0 (academic agricultural market monitoring)',
            'Accept': 'text/html,application/xhtml+xml',
        }
        req = urllib.request.Request(_SOURCE_URL, headers=headers)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        logger.warning('[AR-Prices] Não foi possível acessar Mercado Central: %s', e)
        return {
            'country_code': _CC,
            'status':       'source_unreachable',
            'message':      f'Mercado Central BA inacessível: {e}',
            'records':      0,
            'source':       _SOURCE_NAME,
            'collected_at': datetime.now().isoformat(),
        }

    items = _parse_price_table(raw)

    if not items:
        logger.info('[AR-Prices] Página acessada mas sem tabela de preços parseável.')
        return {
            'country_code': _CC,
            'status':       'source_no_data',
            'message':      'Mercado Central acessado mas estrutura HTML não contém tabela de preços reconhecível. A estrutura pode ter mudado.',
            'records':      0,
            'source':       _SOURCE_NAME,
            'source_url':   _SOURCE_URL,
            'collected_at': datetime.now().isoformat(),
        }

    # Enriquecer com normalização
    today   = date.today().isoformat()
    records = []
    for item in items:
        price_kg  = calculate_price_per_kg(item['price'], item.get('unit', 'kg'))
        price_usd, conf_usd = convert_to_usd(price_kg or item['price'], _CURRENCY)

        record = {
            'country_code':       _CC,
            'country':            _COUNTRY,
            'market_name':        _SOURCE_NAME,
            'market_type':        'atacado',
            'product':            item['product'],
            'product_normalized': PRODUCT_MAP.get(item['product'].lower(), normalize_product_name(item['product'])),
            'category':           item.get('category', 'hortifruti'),
            'price':              item['price'],
            'currency':           _CURRENCY,
            'unit':               item.get('unit', _UNIT),
            'price_per_kg':       price_kg,
            'price_usd':          price_usd,
            'date':               item.get('date', today),
            'source':             _SOURCE_NAME,
            'source_url':         _SOURCE_URL,
            'source_type':        'real',
            'confidence':         conf_usd if price_usd else 'media',
            'is_fallback':        0,
            'collected_at':       datetime.now().isoformat(),
        }
        records.append(record)

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


def _parse_price_table(html: str) -> list[dict]:
    """
    Extrai preços de tabela HTML do Mercado Central.
    Procura padrões de preço em ARS próximos a nomes de produtos conhecidos.
    """
    items = []
    today = date.today().isoformat()

    # Procura tabelas HTML com preços
    # Padrão: <td>nome_produto</td>...<td>preço</td>
    table_pattern = re.compile(
        r'<tr[^>]*>.*?</tr>', re.DOTALL | re.IGNORECASE
    )
    price_pattern = re.compile(r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)')

    for prod_name, slug in PRODUCT_MAP.items():
        # Procura o nome do produto (case insensitive) seguido de preço na página
        pattern = re.compile(
            rf'\b{re.escape(prod_name)}\b.*?(\d{{2,6}}(?:[.,]\d{{1,2}})?)',
            re.IGNORECASE | re.DOTALL
        )
        matches = pattern.findall(html)
        for match in matches[:1]:  # máximo 1 preço por produto
            try:
                price_str = match.replace('.', '').replace(',', '.')
                price = float(price_str)
                if price < 1 or price > 500000:  # sanidade para ARS
                    continue
                items.append({
                    'product':  prod_name,
                    'price':    price,
                    'unit':     'kg',
                    'category': 'hortifruti',
                    'date':     today,
                })
            except (ValueError, AttributeError):
                continue

    return items
