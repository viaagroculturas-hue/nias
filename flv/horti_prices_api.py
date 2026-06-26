"""
API de Preços de Hortifruti — Brasil
Agrega CEAGESP (diário) + CONAB PROHORT (mensal, 11 CEASAs)
Endpoint: GET /api/hortifruti/precos
"""
import time
import json

_cache = {}
_cache_ttl = 1800  # 30 min

# Mapeamento: slug FLV → nome produto PROHORT
FLV_TO_PROHORT = {
    'tomate':    'Tomate',
    'batata':    'Batata',
    'cebola':    'Cebola',
    'cenoura':   'Cenoura',
    'folhosas':  'Alface',
    'banana':    'Banana',
    'laranja':   'Laranja',
    'maca':      'Maçã',
    'mamao':     'Mamão',
    'melancia':  'Melancia',
}

PROHORT_TO_FLV = {v: k for k, v in FLV_TO_PROHORT.items()}

PRODUCT_META = {
    'tomate':   {'name': 'Tomate',        'icon': '🍅', 'category': 'legume'},
    'batata':   {'name': 'Batata Inglesa','icon': '🥔', 'category': 'legume'},
    'cebola':   {'name': 'Cebola',        'icon': '🧅', 'category': 'legume'},
    'cenoura':  {'name': 'Cenoura',       'icon': '🥕', 'category': 'legume'},
    'folhosas': {'name': 'Alface/Folhosas','icon':'🥬', 'category': 'verdura'},
    'banana':   {'name': 'Banana',        'icon': '🍌', 'category': 'fruta'},
    'laranja':  {'name': 'Laranja',       'icon': '🍊', 'category': 'fruta'},
    'maca':     {'name': 'Maçã',          'icon': '🍎', 'category': 'fruta'},
    'mamao':    {'name': 'Mamão',         'icon': '🟠', 'category': 'fruta'},
    'melancia': {'name': 'Melancia',      'icon': '🍉', 'category': 'fruta'},
}


def _calc_arbitrage(terminals: dict, prohort_name: str) -> dict | None:
    """Calcula melhor oportunidade de compra/venda entre terminais."""
    prices = {
        slug: vals[prohort_name]['price_kg']
        for slug, vals in terminals.items()
        if not slug.startswith('_') and isinstance(vals.get(prohort_name), dict)
        and vals[prohort_name].get('price_kg', 0) > 0
    }
    if len(prices) < 2:
        return None

    best_buy_slug  = min(prices, key=prices.get)
    best_sell_slug = max(prices, key=prices.get)
    buy_price  = prices[best_buy_slug]
    sell_price = prices[best_sell_slug]
    margin_pct = round((sell_price - buy_price) / buy_price * 100, 1) if buy_price else 0

    labels = {
        slug: vals.get('_label', slug)
        for slug, vals in terminals.items()
    }

    return {
        'buy':  {'ceasa': best_buy_slug,  'price_kg': round(buy_price, 2),  'label': labels.get(best_buy_slug, best_buy_slug)},
        'sell': {'ceasa': best_sell_slug, 'price_kg': round(sell_price, 2), 'label': labels.get(best_sell_slug, best_sell_slug)},
        'margin_pct': margin_pct,
        'spread_abs': round(sell_price - buy_price, 2),
        'terminals_compared': len(prices),
    }


def get_horti_prices() -> dict:
    global _cache
    now = time.time()
    if _cache.get('data') and now - _cache.get('ts', 0) < _cache_ttl:
        return _cache['data']

    # ── 1. CEAGESP (diário) ─────────────────────────────────────────
    ceagesp_data: dict = {}
    ceagesp_meta: dict = {}
    try:
        from flv.collectors.ceagesp_live import fetch_ceagesp
        raw = fetch_ceagesp()
        ceagesp_data = raw.get('products', {})
        ceagesp_meta = raw.get('meta', {})
    except Exception as e:
        print(f'[HortiPrices] CEAGESP erro: {e}')

    # ── 2. CONAB PROHORT (mensal, 11 CEASAs) ────────────────────────
    prohort_terminals: dict = {}
    prohort_nacional: dict  = {}
    prohort_meta: dict      = {}
    try:
        from flv.collectors.prohort import fetch_prohort
        raw = fetch_prohort()
        prohort_terminals = raw.get('terminals', {})
        prohort_nacional  = raw.get('nacional', {})
        prohort_meta      = raw.get('meta', {})
    except Exception as e:
        print(f'[HortiPrices] PROHORT erro: {e}')

    # ── 3. Montar resposta por produto ──────────────────────────────
    products_out: dict = {}
    arbitrage_list: list = []

    for flv_slug, prohort_name in FLV_TO_PROHORT.items():
        meta = PRODUCT_META.get(flv_slug, {'name': prohort_name, 'icon': '⬡', 'category': 'outros'})

        # Preço CEAGESP (mais fresco — diário)
        cg = ceagesp_data.get(flv_slug)
        ceagesp_entry = None
        if cg:
            ceagesp_entry = {
                'price_kg':      round(cg.get('price_avg', 0), 2),
                'price_min':     round(cg.get('price_min', 0), 2),
                'price_max':     round(cg.get('price_max', 0), 2),
                'unit':          cg.get('unit', 'kg'),
                'classification': cg.get('classification', ''),
                'product_name':  cg.get('name', ''),
                'date':          cg.get('date', ceagesp_meta.get('date', '')),
                'source':        cg.get('source', 'CEAGESP'),
            }

        # Preço médio nacional PROHORT
        nat = prohort_nacional.get(prohort_name)
        prohort_national_avg = round(nat['price_kg'], 2) if isinstance(nat, dict) else None

        # Preços por terminal PROHORT
        prohort_by_terminal: dict = {}
        for t_slug, t_data in prohort_terminals.items():
            if t_slug.startswith('_'):
                continue
            t_prod = t_data.get(prohort_name)
            if isinstance(t_prod, dict) and t_prod.get('price_kg', 0) > 0:
                prohort_by_terminal[t_slug] = {
                    'price_kg': round(t_prod['price_kg'], 2),
                    'var_pct':  round((t_prod.get('var_pct') or 0) * 100, 1),
                    'label':    t_data.get('_label', t_slug),
                }

        # Arbitragem entre terminais
        arb = _calc_arbitrage(prohort_terminals, prohort_name)
        if arb and arb['margin_pct'] > 5:
            arbitrage_list.append({
                'slug':       flv_slug,
                'produto':    meta['name'],
                'icon':       meta['icon'],
                'margin_pct': arb['margin_pct'],
                'buy':        arb['buy'],
                'sell':       arb['sell'],
                'spread_abs': arb['spread_abs'],
            })

        # Preço de referência consolidado (CEAGESP > PROHORT nacional)
        ref_price = (ceagesp_entry['price_kg'] if ceagesp_entry else None) or prohort_national_avg

        products_out[flv_slug] = {
            'slug':         flv_slug,
            'name':         meta['name'],
            'icon':         meta['icon'],
            'category':     meta['category'],
            'price_ref_kg': ref_price,
            'ceagesp':      ceagesp_entry,
            'prohort': {
                'national_avg': prohort_national_avg,
                'period':       prohort_meta.get('period', ''),
                'terminals':    prohort_by_terminal,
            },
            'arbitrage': arb,
        }

    # Top arbitragens ordenadas por margem
    arbitrage_list.sort(key=lambda x: x['margin_pct'], reverse=True)

    # ── 4. Resumo por terminal ───────────────────────────────────────
    terminals_summary: dict = {}
    for t_slug, t_data in prohort_terminals.items():
        if t_slug.startswith('_'):
            continue
        count = sum(
            1 for k, v in t_data.items()
            if not k.startswith('_') and isinstance(v, dict) and v.get('price_kg', 0) > 0
        )
        terminals_summary[t_slug] = {
            'label':          t_data.get('_label', t_slug),
            'products_count': count,
        }

    result = {
        'status': 'ok',
        'meta': {
            'updated_at':  time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'sources': {
                'ceagesp': {
                    'date':        ceagesp_meta.get('date', ''),
                    'products':    len(ceagesp_data),
                    'terminal':    'CEAGESP-SP',
                    'frequency':   'diária (seg/qua/sex)',
                },
                'prohort': {
                    'period':      prohort_meta.get('period', ''),
                    'terminals':   prohort_meta.get('terminals_count', 0),
                    'products':    len(prohort_meta.get('products', [])),
                    'frequency':   'mensal (CONAB)',
                    'xlsx_url':    prohort_meta.get('xlsx_url', ''),
                },
            },
            'products_count':  len(products_out),
            'terminals_count': len(terminals_summary),
        },
        'products':       products_out,
        'terminals':      terminals_summary,
        'arbitrage_top':  arbitrage_list[:8],
    }

    _cache['data'] = result
    _cache['ts']   = now
    return result


def handle_horti_prices(handler):
    """HTTP handler para GET /api/hortifruti/precos."""
    from urllib.parse import urlparse, parse_qs
    params = parse_qs(urlparse(handler.path).query)
    force  = params.get('refresh', ['0'])[0] in ('1', 'true')

    if force:
        global _cache
        _cache = {}

    try:
        data = get_horti_prices()
        body = json.dumps(data, ensure_ascii=False).encode()
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json; charset=utf-8')
        handler.send_header('Cache-Control', 'public, max-age=900')
        handler.end_headers()
        handler.wfile.write(body)
    except Exception as e:
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.end_headers()
        handler.wfile.write(json.dumps({'status': 'error', 'error': str(e)}).encode())
