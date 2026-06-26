"""NIAS — Módulo de Previsão de Demanda Regional (demand_api.py)
Endpoint: GET /api/nias/demanda?product=tomate&region=SP&days=15
"""
import json
import math
from datetime import datetime, timedelta
from flv.db import get_conn

SEASONALITY = {
    'tomate':  [0.8, 0.9, 1.2, 1.3, 1.1, 0.9, 0.8, 0.8, 1.0, 1.1, 1.2, 1.0],
    'cebola':  [1.1, 1.2, 1.0, 0.8, 0.7, 0.9, 1.1, 1.3, 1.2, 1.0, 0.9, 1.0],
    'batata':  [0.9, 1.0, 1.1, 1.2, 1.0, 0.9, 0.8, 0.9, 1.0, 1.1, 1.1, 1.0],
    'soja':    [1.0, 1.1, 1.2, 0.9, 0.8, 0.8, 0.9, 1.0, 1.1, 1.1, 1.0, 1.0],
    'milho':   [1.1, 1.0, 0.9, 0.8, 0.9, 1.0, 1.1, 1.1, 1.0, 0.9, 1.0, 1.1],
    'banana':  [1.0, 1.0, 0.9, 0.9, 1.0, 1.1, 1.1, 1.0, 1.0, 1.0, 0.9, 1.0],
    'default': [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
}

PRICE_REF = {
    'tomate': 4.5, 'cebola': 2.8, 'batata': 1.9,
    'soja': 155.0, 'milho': 72.0, 'banana': 2.1,
}


def _parse_qs(path):
    params = {}
    if '?' in path:
        qs = path.split('?', 1)[1]
        for part in qs.split('&'):
            if '=' in part:
                k, v = part.split('=', 1)
                params[k] = v.replace('+', ' ').replace('%20', ' ')
    return params


def _fetch_history(product, region):
    conn = get_conn()
    region_pattern = f'%{region}%' if region else '%'
    try:
        rows = conn.execute(
            """SELECT date, price_brl, terminal_name FROM flv_prices
               WHERE culture_slug = ? AND terminal_name LIKE ?
               ORDER BY date DESC LIMIT 90""",
            (product, region_pattern)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        pass
    # fallback: try flv_ceasa_prices via join
    try:
        rows = conn.execute(
            """SELECT fp.price_date AS date, fp.price_avg AS price_brl, fp.terminal AS terminal_name
               FROM flv_ceasa_prices fp
               JOIN flv_cultures fc ON fc.id = fp.culture_id
               WHERE fc.slug = ? AND fp.terminal LIKE ?
               ORDER BY fp.price_date DESC LIMIT 90""",
            (product, region_pattern)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def handle_demanda(handler, path):
    try:
        params = _parse_qs(path)
        product = params.get('product', 'tomate').lower()
        region = params.get('region', '')
        try:
            forecast_days = max(1, min(90, int(params.get('days', 15))))
        except ValueError:
            forecast_days = 15

        seasonality = SEASONALITY.get(product, SEASONALITY['default'])
        history = _fetch_history(product, region)
        data_source = 'db' if history else 'referencia'

        # Compute prices
        prices = [float(r['price_brl']) for r in history if r.get('price_brl') is not None]

        if prices:
            avg_price = sum(prices) / len(prices)
            recent_7 = prices[:7] if len(prices) >= 7 else prices
            recent_30 = prices[:30] if len(prices) >= 30 else prices
            avg_7 = sum(recent_7) / len(recent_7)
            avg_30 = sum(recent_30) / len(recent_30)
            trend_factor = avg_7 / avg_30 if avg_30 else 1.0
            current_price = prices[0] if prices else None
        else:
            base_price = PRICE_REF.get(product, 3.0)
            avg_price = base_price
            trend_factor = 1.0
            current_price = None

        # Trend label
        if trend_factor > 1.05:
            trend_label = 'alta'
        elif trend_factor < 0.95:
            trend_label = 'baixa'
        else:
            trend_label = 'estavel'

        # Baseline demand index (current month seasonality)
        today = datetime.now()
        baseline_idx = seasonality[today.month - 1]

        # Confidence based on data availability
        if len(prices) >= 30:
            confidence = 'alta'
        elif len(prices) >= 7:
            confidence = 'media'
        else:
            confidence = 'baixa'

        # Generate forecast
        forecast = []
        for i in range(1, forecast_days + 1):
            future_date = today + timedelta(days=i)
            month_idx = future_date.month - 1
            sea_factor = seasonality[month_idx]
            demand_index = round(sea_factor * trend_factor, 4)
            price_forecast = round(avg_price * sea_factor * trend_factor, 2)
            forecast.append({
                'date': future_date.strftime('%Y-%m-%d'),
                'demand_index': demand_index,
                'price_forecast': price_forecast,
                'confidence': confidence,
            })

        # Seasonality note
        max_month = seasonality.index(max(seasonality)) + 1
        min_month = seasonality.index(min(seasonality)) + 1
        month_names = ['jan','fev','mar','abr','mai','jun','jul','ago','set','out','nov','dez']
        seasonality_note = (
            f"Alta demanda em {month_names[max_month-1]}, "
            f"baixa em {month_names[min_month-1]}."
        )

        result = {
            'product': product,
            'region': region or 'Brasil',
            'forecast_days': forecast_days,
            'current_price': current_price,
            'baseline_demand_index': round(baseline_idx, 4),
            'forecast': forecast,
            'seasonality_note': seasonality_note,
            'trend': trend_label,
            'trend_factor': round(trend_factor, 4),
            'history_points': len(prices),
            'data_source': data_source,
        }

        data = json.dumps(result).encode()
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(data)

    except Exception as e:
        err = json.dumps({'error': str(e)}).encode()
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)
