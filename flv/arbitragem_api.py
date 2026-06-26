"""NIAS - Arbitragem API: calcula spreads de preço entre CEASAs."""
import json
import math
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

from flv.db import get_conn

# Distâncias aproximadas (km) entre CEASAs principais
_DISTANCIAS = {
    ('CEAGESP', 'CEASA-RJ'): 450,
    ('CEAGESP', 'CEASA-PR'): 380,
    ('CEAGESP', 'CEASA-MG'): 600,
    ('CEAGESP', 'CEASA-RS'): 1100,
    ('CEASA-GO', 'CEAGESP'): 900,
    # simétricas
    ('CEASA-RJ', 'CEAGESP'): 450,
    ('CEASA-PR', 'CEAGESP'): 380,
    ('CEASA-MG', 'CEAGESP'): 600,
    ('CEASA-RS', 'CEAGESP'): 1100,
    ('CEAGESP', 'CEASA-GO'): 900,
}

# R$/kg/100km para hortaliças
_FRETE_POR_100KM = 0.18
# Volume médio caminhão (toneladas)
_VOL_CAMINHAO_KG = 20_000
# Margem mínima para viabilidade (15%)
_MARGEM_MINIMA = 0.15


def _normalizar_terminal(nome):
    """Normaliza nome do terminal para chave de distância."""
    n = nome.upper().strip()
    mapa = {
        'CEAGESP': 'CEAGESP',
        'SP': 'CEAGESP',
        'SAO PAULO': 'CEAGESP',
        'RJ': 'CEASA-RJ',
        'RIO DE JANEIRO': 'CEASA-RJ',
        'PR': 'CEASA-PR',
        'PARANA': 'CEASA-PR',
        'MG': 'CEASA-MG',
        'MINAS GERAIS': 'CEASA-MG',
        'RS': 'CEASA-RS',
        'RIO GRANDE DO SUL': 'CEASA-RS',
        'GO': 'CEASA-GO',
        'GOIAS': 'CEASA-GO',
    }
    for k, v in mapa.items():
        if k in n:
            return v
    return n


def _distancia_km(a, b):
    ka = _normalizar_terminal(a)
    kb = _normalizar_terminal(b)
    return _DISTANCIAS.get((ka, kb)) or _DISTANCIAS.get((kb, ka))


def _custo_frete(dist_km):
    """Custo frete em R$/kg para distância dada."""
    return _FRETE_POR_100KM * (dist_km / 100.0)


def _get_product_from_path(path):
    """Extrai parâmetro product da query string."""
    if '?' in path:
        qs = path.split('?', 1)[1]
        params = parse_qs(qs)
        return params.get('product', ['tomate'])[0].lower().strip()
    return 'tomate'


def _fetch_precos(product):
    conn = get_conn()
    # Tenta flv_prices primeiro, depois flv_ceasa_prices (tabela real do schema)
    rows = []
    for sql in [
        (
            "SELECT terminal_name, AVG(price_brl) as price, MAX(date) as last_date "
            "FROM flv_prices WHERE culture_slug = ? AND date >= date('now','-7 days') "
            "GROUP BY terminal_name HAVING COUNT(*) >= 2",
            (product,)
        ),
        (
            "SELECT p.terminal, AVG(p.price_avg) as price, MAX(p.price_date) as last_date "
            "FROM flv_ceasa_prices p "
            "JOIN flv_cultures c ON c.id = p.culture_id "
            "WHERE c.slug = ? AND p.price_date >= date('now','-7 days') "
            "GROUP BY p.terminal HAVING COUNT(*) >= 2",
            (product,)
        ),
    ]:
        try:
            result = conn.execute(sql[0], sql[1]).fetchall()
            if result:
                rows = [dict(r) for r in result]
                # normaliza chave
                for r in rows:
                    if 'terminal' in r and 'terminal_name' not in r:
                        r['terminal_name'] = r.pop('terminal')
                break
        except Exception:
            continue
    return rows


def handle_arbitragem(handler, path):
    try:
        product = _get_product_from_path(path)
        generated_at = datetime.now(timezone.utc).isoformat()

        rows = _fetch_precos(product)

        if len(rows) < 2:
            payload = {
                "product": product,
                "opportunities": [],
                "best_spread": 0.0,
                "generated_at": generated_at,
                "message": (
                    f"Dados insuficientes para '{product}'. "
                    "São necessários preços em pelo menos 2 terminais nos últimos 7 dias."
                )
            }
            out = json.dumps(payload).encode()
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(out)
            return

        # Calcula todos os pares
        opportunities = []
        for i in range(len(rows)):
            for j in range(len(rows)):
                if i == j:
                    continue
                buy = rows[i]
                sell = rows[j]
                buy_name = buy.get('terminal_name', '')
                sell_name = sell.get('terminal_name', '')
                buy_price = float(buy.get('price', 0))
                sell_price = float(sell.get('price', 0))

                if sell_price <= buy_price:
                    continue

                spread_abs = sell_price - buy_price
                spread_pct = (spread_abs / buy_price) * 100 if buy_price > 0 else 0

                dist = _distancia_km(buy_name, sell_name)
                if dist is None:
                    freight = None
                    freight_str = "distância desconhecida"
                    net_margin_pct = spread_pct - 15  # estimativa conservadora
                else:
                    freight = _custo_frete(dist)
                    freight_str = f"{freight:.4f}"
                    net_margin_pct = ((spread_abs - freight) / buy_price) * 100

                viable = net_margin_pct >= (_MARGEM_MINIMA * 100)

                if viable:
                    rec = (
                        f"COMPRAR em {buy_name} a R${buy_price:.2f}/kg e "
                        f"VENDER em {sell_name} a R${sell_price:.2f}/kg. "
                        f"Margem líquida estimada: {net_margin_pct:.1f}%."
                    )
                else:
                    rec = (
                        f"Spread de {spread_pct:.1f}% entre {buy_name} e {sell_name} "
                        f"não cobre frete + margem mínima ({_MARGEM_MINIMA*100:.0f}%)."
                    )

                opportunities.append({
                    "buy_at": buy_name,
                    "sell_at": sell_name,
                    "buy_price": round(buy_price, 4),
                    "sell_price": round(sell_price, 4),
                    "spread_pct": round(spread_pct, 2),
                    "freight_cost_per_kg": round(freight, 4) if freight is not None else None,
                    "net_margin_pct": round(net_margin_pct, 2),
                    "viable": viable,
                    "recommendation": rec
                })

        # Ordena por net_margin_pct desc
        opportunities.sort(key=lambda x: x['net_margin_pct'], reverse=True)

        best_spread = max((o['spread_pct'] for o in opportunities), default=0.0)

        payload = {
            "product": product,
            "opportunities": opportunities,
            "best_spread": round(best_spread, 2),
            "generated_at": generated_at
        }

        out = json.dumps(payload).encode()
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(out)

    except Exception as e:
        err = json.dumps({'error': str(e)}).encode()
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)
