"""
Registry central dos coletores de preços sul-americanos.

Cada coletor retorna lista de dicts no formato padronizado NIAS,
ou dict de erro com status='source_not_available'.
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Formato de retorno obrigatório:
PRICE_RECORD_TEMPLATE = {
    'country_code':       str,   # ISO 2 letras
    'country':            str,   # Nome do país
    'market_name':        str,   # Mercado de referência
    'market_type':        str,   # 'atacado' | 'varejo' | 'produtor'
    'product':            str,   # nome original
    'product_normalized': str,   # slug NIAS
    'category':           str,   # 'fruta' | 'legume' | 'verdura' | 'grao'
    'price':              float, # preço na moeda local
    'currency':           str,   # ISO 4217
    'unit':               str,   # unidade original
    'price_per_kg':       float, # preço/kg na moeda local (None se não conversível)
    'price_usd':          float, # preço USD (None se não disponível)
    'date':               str,   # YYYY-MM-DD
    'source':             str,   # nome da fonte
    'source_url':         str,
    'source_type':        str,   # 'real' | 'estimated' | 'fallback'
    'confidence':         str,   # 'alta' | 'media' | 'baixa'
    'is_fallback':        int,   # 0 = real, 1 = fallback
    'collected_at':       str,   # ISO timestamp
}


def _error_result(country_code: str, status: str, message: str) -> dict:
    return {
        'country_code': country_code,
        'status':       status,
        'message':      message,
        'records':      0,
        'collected_at': datetime.now().isoformat(),
    }


def collect_all_countries(countries: list[str] = None) -> dict:
    """
    Executa todos os coletores disponíveis.
    Retorna dict: country_code → {status, records, items, errors}.
    Falha de um país não quebra os demais.
    """
    from flv.south_america_price_sources import SOUTH_AMERICA_PRICE_SOURCES

    if countries is None:
        countries = list(SOUTH_AMERICA_PRICE_SOURCES.keys())

    results = {}

    for cc in countries:
        logger.info('[Prices-SA] %s iniciando coleta', cc)
        try:
            result = _collect_country(cc)
            results[cc] = result
            n = result.get('records', 0)
            status = result.get('status', '?')
            logger.info('[Prices-SA] %s %s records=%d', cc, status, n)
        except Exception as e:
            logger.error('[Prices-SA] %s ERRO: %s', cc, e)
            results[cc] = _error_result(cc, 'error', str(e))

    total = sum(r.get('records', 0) for r in results.values())
    logger.info('[Prices-SA] DONE total_records=%d', total)
    return results


def _collect_country(country_code: str) -> dict:
    """Despacha para o coletor correto pelo country_code."""
    cc = country_code.upper()

    if cc == 'BR':
        # Brasil já usa o coletor existente — não reimplementar
        return {
            'country_code': 'BR',
            'status': 'managed_by_ceasa_collector',
            'records': 0,
            'message': 'Preços BR gerenciados por flv/collectors/ceasa.py (CONAB/PROHORT).',
        }

    if cc == 'AR':
        from flv.collectors.prices.ar_prices import fetch as ar_fetch
        return ar_fetch()

    if cc == 'CL':
        from flv.collectors.prices.cl_odepa import fetch as cl_fetch
        return cl_fetch()

    if cc == 'PE':
        from flv.collectors.prices.pe_midagri import fetch as pe_fetch
        return pe_fetch()

    if cc == 'UY':
        from flv.collectors.prices.uy_uam import fetch as uy_fetch
        return uy_fetch()

    if cc == 'CO':
        from flv.collectors.prices.co_sipsa import fetch as co_fetch
        return co_fetch()

    # PY, EC, BO — ainda não implementados
    return _error_result(cc, 'source_pending',
                         f'Coletor para {cc} ainda não implementado. Fonte identificada mas pendente.')
