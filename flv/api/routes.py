"""FLV API Routes — Handler for /api/flv/* endpoints."""
import json, urllib.parse
from datetime import datetime

def handle_flv(handler, path):
    """Route dispatcher for FLV API endpoints."""
    parsed = urllib.parse.urlparse(path)
    route = parsed.path
    params = dict(urllib.parse.parse_qsl(parsed.query))

    try:
        if route == '/api/flv/cultures':
            data = _get_cultures()
        elif route.startswith('/api/flv/prices'):
            data = _get_prices(params)
        elif route.startswith('/api/flv/predictions/'):
            slug = route.split('/api/flv/predictions/')[-1].split('?')[0]
            data = _get_predictions(slug, params)
        elif route == '/api/flv/alerts':
            data = _get_alerts(params)
        elif route.startswith('/api/flv/heatmap'):
            data = _get_heatmap(params)
        elif route.startswith('/api/flv/municipality/'):
            parts = route.split('/')
            ibge = parts[4] if len(parts) > 4 else ''
            data = _get_municipality(ibge)
        elif route.startswith('/api/flv/backtest'):
            data = _get_backtest(params)
        elif route.startswith('/api/flv/climate/'):
            ibge = route.split('/api/flv/climate/')[-1].split('?')[0]
            data = _get_climate(ibge, params)
        elif route == '/api/flv/strategic-intelligence':
            data = _get_strategic_intelligence_summary(params)
        elif route.startswith('/api/flv/strategic-intelligence/'):
            domain = route.split('/api/flv/strategic-intelligence/')[-1].split('?')[0]
            data = _get_strategic_intelligence_domain(domain, params)
        elif route == '/api/flv/pipeline/run':
            data = _trigger_pipeline()
        else:
            _send_json(handler, 404, {'error': 'FLV route not found', 'path': route})
            return

        _send_json(handler, 200, data)
    except Exception as e:
        _send_json(handler, 500, {'error': str(e)})

def _send_json(handler, code, data):
    handler.send_response(code)
    handler.send_header('Content-Type', 'application/json')
    origin = handler.headers.get('Origin')
    allowed = {'https://nias.onrender.com', 'http://localhost:5000', 'http://127.0.0.1:5000'}
    handler.send_header('Access-Control-Allow-Origin', origin if origin in allowed else 'https://nias.onrender.com')
    handler.send_header('Vary', 'Origin')
    handler.end_headers()
    handler.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

def _get_cultures():
    from flv.db import query
    return query("SELECT id, slug, name_pt, category, unit, shelf_life_days, seasonality_json, main_producers FROM flv_cultures ORDER BY name_pt")

def _get_prices(params):
    from flv.db import query
    culture = params.get('culture', 'tomate')
    terminal = params.get('terminal', '')
    days = int(params.get('days', '90'))

    sql = """
        SELECT p.price_date as date, p.price_avg as price, p.price_min, p.price_max, p.terminal, p.source
        FROM flv_ceasa_prices p
        JOIN flv_cultures c ON c.id = p.culture_id
        WHERE c.slug = ?
    """
    args = [culture]
    if terminal:
        sql += " AND p.terminal = ?"
        args.append(terminal)
    sql += " ORDER BY p.price_date DESC LIMIT ?"
    args.append(days)

    rows = query(sql, args)

    # Fallback: if terminal filter returned empty, try without terminal
    if not rows and terminal:
        sql2 = """
            SELECT p.price_date as date, p.price_avg as price, p.price_min, p.price_max, p.terminal, p.source
            FROM flv_ceasa_prices p
            JOIN flv_cultures c ON c.id = p.culture_id
            WHERE c.slug = ?
            ORDER BY p.price_date DESC LIMIT ?
        """
        rows = query(sql2, [culture, days])

    rows.reverse()

    # Compute SMAs
    prices = [r['price'] for r in rows]
    sma7 = _sma(prices, 7)
    sma21 = _sma(prices, 21)

    return {
        'culture': culture,
        'terminal': terminal or 'all',
        'series': rows,
        'sma7': sma7,
        'sma21': sma21,
        'count': len(rows),
        'source': 'CONAB/CEASA',
    }

def _sma(values, window):
    result = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(None)
        else:
            avg = sum(values[i - window + 1:i + 1]) / window
            result.append(round(avg, 2))
    return result

def _get_predictions(slug, params):
    terminal = params.get('terminal', '')
    horizon = int(params.get('horizon', '15'))
    from flv.model.prophet_model import predict
    return predict(slug, terminal or None, horizon=horizon)

def _get_alerts(params):
    from flv.db import query
    severity = params.get('severity', 'all')
    region = params.get('region', 'all')

    sql = """
        SELECT a.*, c.slug as culture_slug, c.name_pt as culture_name,
               m.name as mun_name, m.state_uf
        FROM flv_alerts a
        LEFT JOIN flv_cultures c ON c.id = a.culture_id
        LEFT JOIN flv_municipalities m ON m.id = a.mun_id
        WHERE a.valid_until > datetime('now')
    """
    args = []
    if severity != 'all':
        sql += " AND a.severity = ?"
        args.append(severity)
    if region != 'all':
        sql += " AND a.region_key = ?"
        args.append(region)
    sql += " ORDER BY CASE a.severity WHEN 'vermelho' THEN 0 WHEN 'laranja' THEN 1 ELSE 2 END, a.created_at DESC"

    return query(sql, args)

def _get_heatmap(params):
    from flv.db import query
    culture = params.get('culture', 'tomate')

    sql = """
        SELECT m.ibge_code, m.name, m.state_uf, m.lat, m.lon,
               mc.area_mha,
               (SELECT ndvi_value FROM flv_ndvi WHERE mun_id=m.id ORDER BY obs_date DESC LIMIT 1) as ndvi,
               (SELECT price_avg FROM flv_ceasa_prices p JOIN flv_cultures c ON c.id=p.culture_id
                WHERE c.slug=? ORDER BY p.price_date DESC LIMIT 1) as last_price,
               (SELECT severity FROM flv_alerts a JOIN flv_cultures c ON c.id=a.culture_id
                WHERE c.slug=? AND a.mun_id=m.id AND a.valid_until > datetime('now')
                ORDER BY CASE severity WHEN 'vermelho' THEN 0 WHEN 'laranja' THEN 1 ELSE 2 END LIMIT 1) as alert_severity
        FROM flv_municipalities m
        LEFT JOIN flv_mun_culture mc ON mc.mun_id = m.id
        WHERE m.is_producer = 1
    """
    return query(sql, (culture, culture))

def _get_municipality(ibge):
    from flv.db import query

    mun = query("SELECT * FROM flv_municipalities WHERE ibge_code=?", (ibge,))
    if not mun:
        return {'error': 'Municipality not found'}
    mun = mun[0]

    production = query("""
        SELECT c.slug, c.name_pt, p.year, p.production_tons, p.area_harvested_ha
        FROM flv_production p JOIN flv_cultures c ON c.id=p.culture_id
        WHERE p.mun_id=? ORDER BY p.year DESC
    """, (mun['id'],))

    prices = query("""
        SELECT c.slug, p.price_date, p.price_avg, p.terminal
        FROM flv_ceasa_prices p JOIN flv_cultures c ON c.id=p.culture_id
        WHERE p.terminal = ? ORDER BY p.price_date DESC LIMIT 50
    """, (mun.get('ceasa_ref', ''),))

    alerts = query("""
        SELECT a.*, c.name_pt as culture_name
        FROM flv_alerts a LEFT JOIN flv_cultures c ON c.id=a.culture_id
        WHERE a.mun_id=? AND a.valid_until > datetime('now')
        ORDER BY a.created_at DESC
    """, (mun['id'],))

    ndvi = query("""
        SELECT obs_date, ndvi_value FROM flv_ndvi
        WHERE mun_id=? ORDER BY obs_date DESC LIMIT 30
    """, (mun['id'],))

    return {
        'municipality': mun,
        'production': production,
        'prices': prices,
        'alerts': alerts,
        'ndvi': ndvi,
    }

def _get_backtest(params):
    from flv.db import query
    culture = params.get('culture', 'tomate')
    # Return accuracy metrics from flv_accuracy table
    sql = """
        SELECT AVG(a.mape_pct) as avg_mape, COUNT(*) as n_evals
        FROM flv_accuracy a
        JOIN flv_predictions p ON p.id = a.prediction_id
        JOIN flv_cultures c ON c.id = p.culture_id
        WHERE c.slug = ?
    """
    rows = query(sql, (culture,))
    return {
        'culture': culture,
        'avg_mape': rows[0]['avg_mape'] if rows else None,
        'n_evaluations': rows[0]['n_evals'] if rows else 0,
        'status': 'insufficient_data' if not rows or not rows[0]['avg_mape'] else 'ok',
    }

def _get_climate(ibge, params):
    from flv.db import query
    days = int(params.get('days', '30'))
    sql = """
        SELECT c.obs_date, c.temp_max_c, c.temp_min_c, c.precip_mm, c.humidity_pct, c.wind_ms, c.source
        FROM flv_climate c JOIN flv_municipalities m ON m.id=c.mun_id
        WHERE m.ibge_code=? ORDER BY c.obs_date DESC LIMIT ?
    """
    rows = query(sql, (ibge, days))
    rows.reverse()
    return {'ibge': ibge, 'climate': rows, 'count': len(rows)}

def _trigger_pipeline():
    import threading
    from flv.pipeline import run_pipeline
    threading.Thread(target=run_pipeline, daemon=True).start()
    return {'status': 'pipeline_started', 'timestamp': datetime.now().isoformat()}

def _get_strategic_intelligence_summary(params):
    from flv.db import query

    obs = params.get('date')
    if not obs:
        rows = query("""
            SELECT obs_date FROM (
                SELECT obs_date FROM flv_rj_satellite_watch
                UNION ALL SELECT obs_date FROM flv_capital_drain
                UNION ALL SELECT obs_date FROM flv_betting_dominance
                UNION ALL SELECT obs_date FROM flv_geopolitical_freight
            ) ORDER BY obs_date DESC LIMIT 1
        """)
        obs = rows[0]['obs_date'] if rows else datetime.now().strftime('%Y-%m-%d')

    rj_rows = query("""
        SELECT abandonment_status, COUNT(*) as count, AVG(abandonment_score) as avg_score
        FROM flv_rj_satellite_watch
        WHERE obs_date=?
        GROUP BY abandonment_status
    """, (obs,))
    drain_rows = query("""
        SELECT state_uf, debt_amount_brl, online_bets_spend_brl, capital_drain_index
        FROM flv_capital_drain
        WHERE obs_date=? AND location_level='state'
        ORDER BY capital_drain_index DESC
        LIMIT 10
    """, (obs,))
    betting_rows = query("""
        SELECT region_key, leading_company, estimated_ggr_brl, market_share_pct, peak_period
        FROM flv_betting_dominance
        WHERE obs_date=?
        ORDER BY estimated_ggr_brl DESC
        LIMIT 10
    """, (obs,))
    freight_rows = query("""
        SELECT route_key, recalculated_freight_brl_t, freight_delta_pct, middle_east_risk_index
        FROM flv_geopolitical_freight
        WHERE obs_date=?
        ORDER BY freight_delta_pct DESC
    """, (obs,))
    demographics = query("""
        SELECT age_band, sex, SUM(debtors_count) as debtors_count, SUM(debt_amount_brl) as debt_amount_brl
        FROM flv_debtor_demographics
        WHERE obs_date=?
        GROUP BY age_band, sex
        ORDER BY debtors_count DESC
        LIMIT 12
    """, (obs,))

    return {
        'obs_date': obs,
        'rj_satellite_watch': rj_rows,
        'capital_drain_top_states': drain_rows,
        'debtor_profile_top_segments': demographics,
        'betting_dominance': betting_rows,
        'geopolitical_freight': freight_rows,
        'sources_note': 'Dados persistidos por StrategicIntelligenceCollector; campos confidence_score/evidence_json indicam origem e confiabilidade.'
    }

def _get_strategic_intelligence_domain(domain, params):
    from flv.db import query

    if domain == 'run':
        from flv.collectors.strategic_intelligence import coletar_inteligencia_estrategica
        return coletar_inteligencia_estrategica()

    limit = int(params.get('limit', '100'))
    state = params.get('state', '').upper()
    city = params.get('city', '')
    domains = {
        'rj-satellite': (
            "SELECT * FROM flv_rj_satellite_watch WHERE 1=1",
            " ORDER BY obs_date DESC, abandonment_score DESC LIMIT ?",
        ),
        'capital-drain': (
            "SELECT * FROM flv_capital_drain WHERE 1=1",
            " ORDER BY obs_date DESC, capital_drain_index DESC LIMIT ?",
        ),
        'debtor-profile': (
            "SELECT * FROM flv_debtor_demographics WHERE 1=1",
            " ORDER BY obs_date DESC, debtors_count DESC LIMIT ?",
        ),
        'betting-dominance': (
            "SELECT * FROM flv_betting_dominance WHERE 1=1",
            " ORDER BY obs_date DESC, estimated_ggr_brl DESC LIMIT ?",
        ),
        'geopolitical-freight': (
            "SELECT * FROM flv_geopolitical_freight WHERE 1=1",
            " ORDER BY obs_date DESC, freight_delta_pct DESC LIMIT ?",
        ),
    }
    if domain not in domains:
        return {'error': 'Strategic intelligence domain not found', 'domain': domain, 'available': sorted(domains.keys()) + ['run']}

    sql, order_sql = domains[domain]
    args = []
    if state and domain in ('rj-satellite', 'capital-drain', 'debtor-profile', 'betting-dominance'):
        sql += " AND state_uf=?"
        args.append(state)
    if city and domain in ('rj-satellite', 'capital-drain', 'debtor-profile'):
        sql += " AND city LIKE ?"
        args.append(f"%{city}%")
    sql += order_sql
    args.append(limit)
    rows = query(sql, args)
    return {'domain': domain, 'items': rows, 'count': len(rows)}
