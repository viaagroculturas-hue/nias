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
        elif route == '/api/flv/pipeline/run':
            data = _trigger_pipeline()
        elif route == '/api/flv/model/health':
            data = _get_model_health(params)
        elif route.startswith('/api/flv/cv/classification/'):
            ident = route.split('/api/flv/cv/classification/')[-1].split('?')[0]
            data = _get_cv_classification(ident, params)
        elif route.startswith('/api/flv/cv/scenes/'):
            ident = route.split('/api/flv/cv/scenes/')[-1].split('?')[0]
            data = _get_cv_scenes(ident, params)
        elif route == '/api/flv/cv/health':
            data = _get_cv_health(params)
        elif route.startswith('/api/flv/cv/yield/'):
            ident = route.split('/api/flv/cv/yield/')[-1].split('?')[0]
            data = _get_cv_yield(ident, params)
        elif route == '/api/flv/cv/anomalies':
            data = _get_cv_anomalies(params)
        elif route == '/api/flv/cv/badge':
            data = _get_cv_badge(params)
        else:
            _send_json(handler, 404, {'error': 'FLV route not found', 'path': route})
            return

        _send_json(handler, 200, data)
    except Exception as e:
        _send_json(handler, 500, {'error': str(e)})

def _send_json(handler, code, data):
    handler.send_response(code)
    handler.send_header('Content-Type', 'application/json')
    handler.send_header('Access-Control-Allow-Origin', '*')
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
    model = params.get('model', 'ensemble')  # 'ensemble' | 'prophet' | 'xgb'
    if model == 'prophet':
        from flv.model.prophet_model import predict
    elif model == 'xgb':
        from flv.model.xgb_model import predict
    else:
        from flv.model.ensemble import predict
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


def _get_model_health(params):
    """MLOps health summary: rolling MAPE per (culture, terminal, model) + retrain status."""
    from flv.db import get_conn
    from flv.model.evaluator import summary
    from flv.model.retrain_controller import MAX_MAPE_PCT, check_triggers

    refresh = params.get('refresh') in ('1', 'true', 'yes')
    conn = get_conn()

    if refresh:
        # Opt-in: caller asked to re-score pending predictions before reading.
        try:
            from flv.model.evaluator import evaluate_predictions
            evaluate_predictions(conn)
        except Exception as e:
            return {'error': f'evaluator_failed: {e}', 'cultures': []}

    cultures = summary(conn)
    triggers = check_triggers(conn)
    trig_keys = {(t['culture_slug'], t['terminal'], t['model_version']): t for t in triggers}
    for row in cultures:
        key = (row['culture'], row['terminal'], row['model_version'])
        t = trig_keys.get(key)
        row['needs_retrain'] = bool(t)
        row['retrain_reason'] = t['reason'] if t else None

    return {
        'thresholds': {'max_mape_30d_pct': MAX_MAPE_PCT},
        'cultures': cultures,
        'pending_triggers': triggers,
        'generated_at': datetime.now().isoformat(),
    }


def _resolve_mun(ident):
    """Resolve a path segment to a (mun_id, ibge_code, name). Accepts id or ibge code."""
    from flv.db import get_conn
    conn = get_conn()
    if ident.isdigit() and len(ident) == 7:
        row = conn.execute(
            "SELECT id, ibge_code, name, state_uf, lat, lon FROM flv_municipalities WHERE ibge_code = ?",
            (ident,),
        ).fetchone()
    else:
        try:
            mid = int(ident)
        except ValueError:
            return None
        row = conn.execute(
            "SELECT id, ibge_code, name, state_uf, lat, lon FROM flv_municipalities WHERE id = ?",
            (mid,),
        ).fetchone()
    return row


def _get_cv_classification(ident, params):
    """Return crop_classification rows for a municipality.

    Accepts either the internal mun_id or the 7-digit IBGE code. Optional
    ?year=YYYY filter. If no rows exist and ?predict=1, attempts on-demand
    inference.
    """
    mun = _resolve_mun(ident)
    if not mun:
        return {'error': 'municipality_not_found', 'ident': ident}

    from flv.db import get_conn
    conn = get_conn()
    year = params.get('year')
    sql = ("SELECT year, predicted_crop, confidence, top_k_json, model_version, "
           "predicted_at FROM flv_crop_classification WHERE mun_id = ?")
    args = [mun['id']]
    if year:
        sql += " AND year = ?"
        args.append(int(year))
    sql += " ORDER BY year DESC, predicted_at DESC LIMIT 10"
    rows = conn.execute(sql, args).fetchall()

    items = []
    for r in rows:
        top_k = None
        if r['top_k_json']:
            try:
                top_k = json.loads(r['top_k_json'])
            except Exception:
                top_k = None
        items.append({
            'year': r['year'],
            'predicted_crop': r['predicted_crop'],
            'confidence': r['confidence'],
            'top_k': top_k,
            'model_version': r['model_version'],
            'predicted_at': r['predicted_at'],
        })

    if not items and params.get('predict') in ('1', 'true', 'yes'):
        try:
            from flv.cv.crop_classifier import predict_one
            target_year = int(year) if year else _latest_lulc_year(conn) or 2024
            live = predict_one(conn, mun['id'], target_year)
            if live:
                items.append({
                    'year': live['year'],
                    'predicted_crop': live['predicted_crop'],
                    'confidence': live['confidence'],
                    'top_k': live['top_k'],
                    'model_version': live['model_version'],
                    'predicted_at': 'live',
                })
        except Exception as e:
            return {'error': f'predict_failed: {e}', 'municipality': dict(mun)}

    return {
        'municipality': {
            'id': mun['id'],
            'ibge_code': mun['ibge_code'],
            'name': mun['name'],
            'state_uf': mun['state_uf'],
        },
        'classifications': items,
        'count': len(items),
    }


def _get_cv_scenes(ident, params):
    """Return recent satellite scenes for a municipality (S2/S1/Landsat metadata)."""
    mun = _resolve_mun(ident)
    if not mun:
        return {'error': 'municipality_not_found', 'ident': ident}

    from flv.db import get_conn
    conn = get_conn()
    platform = params.get('platform')
    max_cloud = params.get('max_cloud')
    limit = int(params.get('limit', '20'))

    sql = ("SELECT platform, scene_id, obs_date, cloud_pct, asset_url, source "
           "FROM flv_sat_scenes WHERE mun_id = ?")
    args = [mun['id']]
    if platform:
        sql += " AND platform = ?"
        args.append(platform)
    if max_cloud:
        sql += " AND (cloud_pct IS NULL OR cloud_pct <= ?)"
        args.append(float(max_cloud))
    sql += " ORDER BY obs_date DESC LIMIT ?"
    args.append(limit)
    rows = conn.execute(sql, args).fetchall()

    scenes = [dict(r) for r in rows]
    by_platform = {}
    for s in scenes:
        by_platform[s['platform']] = by_platform.get(s['platform'], 0) + 1
    return {
        'municipality': {
            'id': mun['id'],
            'ibge_code': mun['ibge_code'],
            'name': mun['name'],
        },
        'scenes': scenes,
        'count': len(scenes),
        'by_platform': by_platform,
    }


def _get_cv_health(params):
    """Summarize the CV classifier: coverage, top classes, last retrain."""
    from flv.db import get_conn
    from flv.cv.crop_classifier import MODEL_VERSION
    conn = get_conn()

    total_muns = conn.execute("SELECT COUNT(*) AS n FROM flv_municipalities").fetchone()['n']
    classified = conn.execute(
        "SELECT COUNT(DISTINCT mun_id) AS n FROM flv_crop_classification "
        "WHERE model_version = ?",
        (MODEL_VERSION,),
    ).fetchone()['n']

    class_dist = conn.execute(
        "SELECT predicted_crop AS crop, COUNT(*) AS n, AVG(confidence) AS avg_conf "
        "FROM flv_crop_classification WHERE model_version = ? "
        "GROUP BY predicted_crop ORDER BY n DESC",
        (MODEL_VERSION,),
    ).fetchall()

    last = conn.execute(
        "SELECT MAX(predicted_at) AS ts FROM flv_crop_classification "
        "WHERE model_version = ?",
        (MODEL_VERSION,),
    ).fetchone()['ts']

    scene_totals = conn.execute(
        "SELECT platform, COUNT(*) AS n FROM flv_sat_scenes GROUP BY platform"
    ).fetchall()

    lulc_years = conn.execute(
        "SELECT DISTINCT year FROM flv_lulc_stats ORDER BY year DESC LIMIT 5"
    ).fetchall()

    return {
        'model_version': MODEL_VERSION,
        'coverage': {
            'total_municipalities': total_muns,
            'classified_municipalities': classified,
            'coverage_pct': round(100.0 * classified / total_muns, 2) if total_muns else 0.0,
        },
        'class_distribution': [dict(r) for r in class_dist],
        'scenes_by_platform': [dict(r) for r in scene_totals],
        'lulc_years_covered': [r['year'] for r in lulc_years],
        'last_prediction_at': last,
        'generated_at': datetime.now().isoformat(),
    }


def _latest_lulc_year(conn):
    row = conn.execute("SELECT MAX(year) AS y FROM flv_lulc_stats").fetchone()
    return row['y'] if row else None


def _get_cv_yield(ident, params):
    """Return yield predictions (ton/ha) for a municipality.

    Query params:
        culture=<slug>   limit to a single culture
        year=YYYY        target year (default: latest in flv_yield_predictions)
        predict=1        force an on-demand prediction when no row exists
    """
    mun = _resolve_mun(ident)
    if not mun:
        return {'error': 'municipality_not_found', 'ident': ident}

    from flv.db import get_conn
    conn = get_conn()
    culture = params.get('culture')
    year = params.get('year')

    sql = ("SELECT culture_slug, year, yield_ton_ha, yield_lower, yield_upper, "
           "ndvi_peak, gdd_total, model_version, predicted_at "
           "FROM flv_yield_predictions WHERE mun_id = ?")
    args = [mun['id']]
    if culture:
        sql += " AND culture_slug = ?"
        args.append(culture)
    if year:
        sql += " AND year = ?"
        args.append(int(year))
    sql += " ORDER BY year DESC, yield_ton_ha DESC LIMIT 50"
    rows = conn.execute(sql, args).fetchall()
    items = [dict(r) for r in rows]

    if not items and params.get('predict') in ('1', 'true', 'yes') and culture:
        try:
            from flv.cv.yield_model import predict_one
            target_year = int(year) if year else _latest_lulc_year(conn) or 2024
            live = predict_one(conn, mun['id'], culture, target_year)
            items.append({
                'culture_slug': culture,
                'year': live['year'],
                'yield_ton_ha': live['yield_ton_ha'],
                'yield_lower': live['yield_lower'],
                'yield_upper': live['yield_upper'],
                'ndvi_peak': live['ndvi_peak'],
                'gdd_total': live['gdd_total'],
                'model_version': live['model_version'],
                'predicted_at': 'live',
                'source': live['source'],
            })
        except Exception as e:
            return {'error': f'predict_failed: {e}', 'municipality': dict(mun)}

    return {
        'municipality': {
            'id': mun['id'],
            'ibge_code': mun['ibge_code'],
            'name': mun['name'],
            'state_uf': mun['state_uf'],
        },
        'yield_predictions': items,
        'count': len(items),
    }


def _get_cv_anomalies(params):
    """Return recent CV-detected anomalies (change-detection).

    Query params:
        since=YYYY-MM-DD   filter to detected_at >= since (default: last 30d)
        kind=<type>        filter by anomaly kind
        severity=<sev>     filter by severity (info|warn|alert)
        limit=N            cap response size (default 100)
    """
    from flv.db import get_conn
    conn = get_conn()
    since = params.get('since')
    if not since:
        from datetime import datetime, timedelta, timezone
        since = (datetime.now(timezone.utc) - timedelta(days=30)).date().isoformat()

    sql = ("SELECT a.id, a.mun_id, m.name AS mun_name, m.state_uf, m.ibge_code, "
           "a.detected_at, a.kind, a.severity, a.delta, a.baseline_value, "
           "a.current_value, a.details_json, a.created_at "
           "FROM flv_cv_anomalies a "
           "JOIN flv_municipalities m ON m.id = a.mun_id "
           "WHERE a.detected_at >= ?")
    args = [since]
    if params.get('kind'):
        sql += " AND a.kind = ?"
        args.append(params['kind'])
    if params.get('severity'):
        sql += " AND a.severity = ?"
        args.append(params['severity'])
    limit = int(params.get('limit', '100'))
    sql += " ORDER BY a.detected_at DESC, a.id DESC LIMIT ?"
    args.append(limit)

    rows = conn.execute(sql, args).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        if d.get('details_json'):
            try:
                d['details'] = json.loads(d.pop('details_json'))
            except Exception:
                d['details'] = None
        items.append(d)
    by_kind = {}
    by_severity = {}
    for it in items:
        by_kind[it['kind']] = by_kind.get(it['kind'], 0) + 1
        by_severity[it['severity']] = by_severity.get(it['severity'], 0) + 1
    return {
        'since': since,
        'anomalies': items,
        'count': len(items),
        'by_kind': by_kind,
        'by_severity': by_severity,
    }


def _get_cv_badge(params):
    """Compact payload the dashboard uses to render the 'CV ATIVO' badge.

    Returns a tri-state status that the heavy-client can map to a green/yellow/red
    pill without computing anything on the client. States:
        - 'active'    : classifier rodou recentemente, sem anomalias alert
        - 'alerting'  : ao menos uma anomalia severidade 'alert' nas ultimas 72h
        - 'degraded'  : sem classificaçoes recentes ou dados insuficientes
    """
    from flv.db import get_conn
    from flv.cv.crop_classifier import MODEL_VERSION as CLF_VERSION
    conn = get_conn()
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    alert_window = (now - timedelta(hours=72)).date().isoformat()
    stale_window = (now - timedelta(days=14)).isoformat()

    last_pred = conn.execute(
        "SELECT MAX(predicted_at) AS ts FROM flv_crop_classification WHERE model_version = ?",
        (CLF_VERSION,),
    ).fetchone()['ts']
    alerts = conn.execute(
        "SELECT COUNT(*) AS n FROM flv_cv_anomalies "
        "WHERE severity = 'alert' AND detected_at >= ?",
        (alert_window,),
    ).fetchone()['n']
    warns = conn.execute(
        "SELECT COUNT(*) AS n FROM flv_cv_anomalies "
        "WHERE severity = 'warn' AND detected_at >= ?",
        (alert_window,),
    ).fetchone()['n']
    classified = conn.execute(
        "SELECT COUNT(DISTINCT mun_id) AS n FROM flv_crop_classification "
        "WHERE model_version = ?",
        (CLF_VERSION,),
    ).fetchone()['n']

    if not last_pred or last_pred < stale_window or classified == 0:
        status = 'degraded'
        label = 'CV INATIVO'
    elif alerts > 0:
        status = 'alerting'
        label = f'CV ATIVO • {alerts} alerta' + ('s' if alerts != 1 else '')
    else:
        status = 'active'
        label = 'CV ATIVO'

    return {
        'status': status,
        'label': label,
        'model_version': CLF_VERSION,
        'last_prediction_at': last_pred,
        'classified_municipalities': classified,
        'alerts_72h': alerts,
        'warnings_72h': warns,
        'generated_at': now.isoformat(),
    }
