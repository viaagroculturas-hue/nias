"""
NIAS Price Normalizer — normalização de produtos, moedas e unidades.

Permite comparação regional entre preços de diferentes países da América do Sul
sem distorcer a análise. Quando a conversão não está disponível ou é imprecisa,
retorna confidence='baixa' e não gera comparação.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Optional

# ─── Mapa de nomes de produtos → slug normalizado ─────────────────────────────
# Chave: variações locais (pt, es) → valor: slug canônico NIAS
PRODUCT_NAME_MAP: dict[str, str] = {
    # Tomate
    'tomate': 'tomate', 'tomate mesa': 'tomate', 'tomate carmem': 'tomate',
    'tomate longa vida': 'tomate', 'tomato': 'tomate',
    # Cebola
    'cebola': 'cebola', 'cebolla': 'cebola', 'cebolla blanca': 'cebola',
    'cebolla morada': 'cebola', 'cebolla nacional': 'cebola',
    # Batata
    'batata': 'batata', 'batata inglesa': 'batata', 'papa': 'batata',
    'patata': 'batata', 'papa amarilla': 'batata', 'papa huayro': 'batata',
    'papa blanca': 'batata', 'papa negra': 'batata', 'papa pastusa': 'batata', 'papa criolla': 'batata',
    # Alho
    'alho': 'alho', 'ajo': 'alho', 'ajo nacional': 'alho', 'garlic': 'alho',
    # Pimentão
    'pimentao': 'pimentao', 'pimentão': 'pimentao', 'pimiento': 'pimentao',
    'pimiento verde': 'pimentao', 'pimiento rojo': 'pimentao',
    # Cenoura
    'cenoura': 'cenoura', 'zanahoria': 'cenoura', 'carrot': 'cenoura',
    # Banana
    'banana': 'banana', 'banano': 'banana', 'plátano': 'banana',
    'platano': 'banana', 'banana prata': 'banana', 'banana nanica': 'banana',
    # Laranja
    'laranja': 'laranja', 'naranja': 'laranja', 'orange': 'laranja',
    'laranja pera': 'laranja',
    # Manga
    'manga': 'manga', 'mango': 'manga', 'manga tommy': 'manga',
    # Uva
    'uva': 'uva', 'uva italia': 'uva', 'uva niagara': 'uva',
    'vid': 'uva', 'grape': 'uva',
    # Maçã
    'maca': 'maca', 'maca fuji': 'maca', 'maca gala': 'maca',
    'manzana': 'maca', 'manzana fuji': 'maca', 'manzana gala': 'maca',
    # Morango
    'morango': 'morango', 'fresa': 'morango', 'frutilla': 'morango',
    'strawberry': 'morango',
    # Abacate
    'abacate': 'abacate', 'palto': 'abacate', 'aguacate': 'abacate',
    'avocado': 'abacate',
    # Mamão
    'mamao': 'mamao', 'mamão': 'mamao', 'papaya': 'mamao',
    'lechosa': 'mamao',
    # Melão
    'melao': 'melao', 'melão': 'melao', 'melon': 'melao',
    # Abacaxi
    'abacaxi': 'abacaxi', 'piña': 'abacaxi', 'pineapple': 'abacaxi',
    # Folhosas
    'alface': 'folhosas', 'lechuga': 'folhosas', 'repolho': 'folhosas',
    'couve': 'folhosas', 'espinaca': 'folhosas', 'repollo': 'folhosas',
    # Limão
    'limao': 'limao', 'limão': 'limao', 'limon': 'limao', 'lemon': 'limao',
    'limón': 'limao',
    # Quinua
    'quinua': 'quinua', 'quinoa': 'quinua',
    # Mandioca
    'mandioca': 'mandioca', 'yuca': 'mandioca', 'cassava': 'mandioca',
}

# ─── Mapa de unidades → kg equivalente ────────────────────────────────────────
# Valor: multiplicador para converter para kg
UNIT_TO_KG: dict[str, float] = {
    'kg':       1.0,
    'g':        0.001,
    't':        1000.0,
    'ton':      1000.0,
    'tonelada': 1000.0,
    'caixa':    23.0,   # caixa padrão CEAGESP ≈ 23kg (varia por produto)
    'cx':       23.0,
    'saco':     60.0,   # saco 60kg (grãos)
    'sc':       60.0,
    'arroba':   15.0,   # arroba = 15kg
    '@':        15.0,
    'quintal':  100.0,
    'qq':       100.0,
    'libra':    0.454,
    'lb':       0.454,
    'unidade':  None,   # depende do produto — não converter
    'un':       None,
    'duzia':    None,   # depende do produto
    'dz':       None,
    'mojo':     None,   # unidade peruana — não converter
}

# ─── Taxas de câmbio de referência (fallback estático) ────────────────────────
# Usadas apenas quando não há taxa disponível no banco.
# Confidence = 'baixa' quando usar estas taxas fixas.
# Fontes deverão atualizar via pipeline de macro.
_FALLBACK_RATES_TO_USD: dict[str, float] = {
    'BRL': 0.185,   # R$ 5,40 / USD (referência 2026)
    'ARS': 0.00095, # ARS ~1050 / USD
    'CLP': 0.00107, # CLP ~935 / USD
    'PEN': 0.265,   # PEN ~3,77 / USD
    'UYU': 0.025,   # UYU ~40 / USD
    'COP': 0.00024, # COP ~4200 / USD
    'PYG': 0.000135,# PYG ~7400 / USD
    'BOB': 0.144,   # BOB ~6,95 / USD
    'USD': 1.0,     # Equador usa USD
}


# ─── Produto ──────────────────────────────────────────────────────────────────

def normalize_product_name(name: str) -> str:
    """
    Converte nome do produto (PT/ES) para slug canônico NIAS.
    Retorna o original normalizado se não encontrar mapeamento.
    """
    if not name:
        return ''
    key = name.strip().lower()
    return PRODUCT_NAME_MAP.get(key, key.replace(' ', '_'))


# ─── Unidade ──────────────────────────────────────────────────────────────────

def normalize_unit(unit: str) -> str:
    """Retorna unidade normalizada em lowercase sem espaços."""
    if not unit:
        return 'kg'
    u = unit.strip().lower().replace('/', '').replace('-', '')
    aliases = {
        'kilo': 'kg', 'kilograma': 'kg', 'kilogram': 'kg',
        'gramo': 'g', 'grama': 'g', 'gram': 'g',
        'caixa': 'caixa', 'box': 'caixa',
        'saco': 'saco', 'bag': 'saco',
        'unidade': 'unidade', 'unit': 'unidade', 'uni': 'unidade',
    }
    return aliases.get(u, u)


def calculate_price_per_kg(price: float, unit: str, product_slug: str = '') -> Optional[float]:
    """
    Converte preço para R$/kg (ou moeda local/kg).
    Retorna None se a conversão não for possível para a unidade.
    """
    if price is None or price <= 0:
        return None
    unit_n = normalize_unit(unit)
    factor = UNIT_TO_KG.get(unit_n)
    if factor is None:
        return None   # unidade não convertível (unidade, duzia, mojo…)
    if factor == 0:
        return None
    return round(price / factor, 4)


# ─── Moeda ────────────────────────────────────────────────────────────────────

def normalize_currency(currency: str) -> str:
    """Normaliza código de moeda para ISO 4217."""
    if not currency:
        return ''
    c = currency.strip().upper()
    aliases = {
        'R$': 'BRL', 'REAIS': 'BRL', 'REAL': 'BRL',
        'U$': 'USD', 'US$': 'USD', 'DOLLAR': 'USD', 'DOLLARS': 'USD',
        '$': 'USD',   # assume USD quando genérico (Equador)
        'PESO': 'ARS', 'PESOS': 'ARS',
        'SOLES': 'PEN', 'SOL': 'PEN',
        'GUARANIS': 'PYG', 'GUARANI': 'PYG',
        'PESOS COLOMBIANOS': 'COP',
        'BOLIVIANOS': 'BOB',
    }
    return aliases.get(c, c)


def get_exchange_rate_to_usd(currency: str, conn: Optional[sqlite3.Connection] = None) -> tuple[float, str]:
    """
    Retorna (taxa_para_usd, confidence).
    Tenta buscar taxa real do banco (tabela flv_macro_indicators).
    Se não encontrar, usa fallback estático com confidence='baixa'.
    """
    currency = normalize_currency(currency)
    if currency == 'USD':
        return 1.0, 'alta'

    # Tentar banco — tabela flv_macro_indicators pode ter taxa de câmbio
    if conn is not None:
        try:
            row = conn.execute("""
                SELECT value FROM flv_macro_indicators
                WHERE indicator = ? AND date >= date('now', '-7 days')
                ORDER BY date DESC LIMIT 1
            """, (f'exchange_rate_{currency}_USD',)).fetchone()
            if row and row[0] and row[0] > 0:
                return float(row[0]), 'media'
        except Exception:
            pass

    rate = _FALLBACK_RATES_TO_USD.get(currency)
    if rate:
        return rate, 'baixa'   # taxa estática — confidence baixa
    return 0.0, 'sem_dado'


def convert_to_usd(price: float, currency: str,
                   conn: Optional[sqlite3.Connection] = None) -> tuple[Optional[float], str]:
    """
    Converte preço para USD.
    Retorna (price_usd, confidence).
    Se a conversão não for confiável, retorna (None, 'sem_dado').
    """
    if price is None or price <= 0:
        return None, 'sem_dado'
    currency = normalize_currency(currency)
    if currency == 'USD':
        return round(price, 4), 'alta'

    rate, conf = get_exchange_rate_to_usd(currency, conn)
    if not rate or rate <= 0:
        return None, 'sem_dado'

    return round(price * rate, 4), conf


# ─── Mercado ──────────────────────────────────────────────────────────────────

def standardize_market_name(name: str, country_code: str = '') -> str:
    """Padroniza nome do mercado para exibição."""
    if not name:
        return country_code or 'Desconhecido'
    n = name.strip()
    known = {
        'CEAGESP': 'CEAGESP (SP/BR)',
        'Mercado Central': f'Mercado Central ({country_code})',
        'SIPSA': 'SIPSA/DANE (CO)',
        'ODEPA': 'ODEPA (CL)',
        'SISAP': 'MIDAGRI/SISAP (PE)',
        'Mercado Modelo': 'Mercado Modelo (UY)',
    }
    for key, display in known.items():
        if key.lower() in n.lower():
            return display
    return n


# ─── Validação regional ───────────────────────────────────────────────────────

def can_compare_regionally(price_items: list[dict]) -> tuple[bool, str]:
    """
    Verifica se é seguro comparar preços entre países.
    Retorna (pode_comparar, motivo).
    """
    if len(price_items) < 2:
        return False, 'Apenas 1 país com dado — sem base para comparação.'

    currencies = {p.get('currency') for p in price_items if p.get('currency')}
    confidences = {p.get('confidence') for p in price_items}

    if 'sem_dado' in confidences:
        return False, 'Algum país sem conversão de moeda disponível.'

    if all(c == 'baixa' for c in confidences):
        return False, 'Todas as taxas de câmbio são fallback estático — comparação imprecisa.'

    usd_prices = [p.get('price_usd') for p in price_items if p.get('price_usd')]
    if len(usd_prices) < 2:
        return False, 'Preços em USD insuficientes para comparação regional.'

    return True, 'ok'
