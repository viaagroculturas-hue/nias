"""
NIAS API Core v1 — Router principal.
Despacha todas as rotas /api/nias/* para os handlers corretos.
"""
import json
from datetime import datetime
from urllib.parse import urlparse, parse_qs

from flv.nias_api import API_VERSION, API_NAME
from flv.nias_api import responses as R


def handle_nias_api_post(handler, raw_path: str):
    """Entry point para POST /api/nias/* (apenas brain/command por enquanto)."""
    import json as _json
    from urllib.parse import urlparse as _up
    parsed = _up(raw_path)
    path = parsed.path.replace('/api/nias/', '').rstrip('/')

    try:
        length = int(handler.headers.get('Content-Length', 0))
        body = _json.loads(handler.rfile.read(length)) if length else {}
    except Exception:
        body = {}

    try:
        if path == 'brain/command':
            result = _brain_command(body)
        else:
            result = R.error(f'POST /api/nias/{path} não suportado.')
        status_code = 200
    except Exception as e:
        result = R.error(str(e), details='Erro interno no NIAS API Brain')
        status_code = 500

    handler.send_response(status_code)
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Content-Type', 'application/json')
    handler.end_headers()
    handler.wfile.write(_json.dumps(result, ensure_ascii=False, default=str).encode())


def handle_nias_api(handler, raw_path: str):
    """Entry point chamado pelo server.py para /api/nias/*."""
    parsed = urlparse(raw_path)
    path = parsed.path.replace('/api/nias/', '').rstrip('/')
    params = parse_qs(parsed.query)

    try:
        result = _dispatch(path, params)
        status_code = 200
    except Exception as e:
        result = R.error(str(e), details='Erro interno no NIAS API Core')
        status_code = 500

    handler.send_response(status_code)
    handler.send_header('Access-Control-Allow-Origin', '*')
    handler.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    handler.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    handler.send_header('Content-Type', 'application/json')
    handler.end_headers()
    handler.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())


def _dispatch(path: str, params: dict) -> dict:
    """Mapeia path para handler."""
    # Status / Health
    if path in ('status', ''):
        return _status()
    if path == 'health':
        return _health()
    if path == 'docs':
        return _docs()

    # Regiões sul-americanas
    if path in ('regions', 'regions/south-america'):
        return _regions(params)

    # Preços
    if path == 'prices/latest':
        return _prices_latest(params)
    if path == 'prices/history':
        return _prices_history(params)

    # Clima
    if path == 'weather/latest':
        return _weather_latest(params)
    if path == 'weather/risk':
        return _weather_risk()
    if path == 'weather/south-america':
        return _weather_south_america()

    # Inteligência
    if path == 'intelligence/weather-price':
        return _intelligence_weather_price(params)
    if path == 'intelligence/opportunities':
        return _intelligence_opportunities()
    if path == 'intelligence/predictions':
        return _intelligence_predictions()
    if path == 'intelligence/alerts':
        return _intelligence_alerts()

    # Relatório
    if path == 'report/daily':
        return _report_daily()

    # Fontes e pipeline
    if path == 'sources/status':
        return _sources_status()
    if path == 'pipeline/status':
        return _pipeline_status()
    if path == 'pipeline/freshness':
        return _pipeline_freshness()
    if path == 'pipeline/runs':
        return _pipeline_runs()

    # Preços Sul-Americanos
    if path == 'prices/south-america':
        return _prices_south_america(params)
    if path == 'prices/sources':
        return _prices_sources()
    if path == 'prices/status':
        return _prices_status()

    # Advisor (Conselheiro NIAS)
    if path == 'advisor' or path == 'advisor/recommendations':
        return _advisor_recommendations(params)
    if path == 'advisor/summary':
        return _advisor_summary()
    if path == 'advisor/opportunities':
        return _advisor_opportunities()
    if path == 'advisor/risks':
        return _advisor_risks()
    if path == 'advisor/thesis':
        return _advisor_thesis(params)
    if path == 'advisor/product':
        return _advisor_product(params)
    if path == 'advisor/country':
        return _advisor_country(params)
    if path == 'advisor/region':
        return _advisor_region(params)

    # Brain (Cérebro NIAS — Inteligência Viva)
    if path in ('brain', 'brain/summary'):
        return _brain_summary()
    if path == 'brain/pulse':
        return _brain_pulse()
    if path == 'brain/events':
        return _brain_events(params)
    if path == 'brain/decisions':
        return _brain_decisions(params)
    if path == 'brain/radar':
        return _brain_radar()
    if path == 'brain/thesis':
        return _brain_thesis(params)
    if path == 'brain/quality':
        return _brain_quality()

    # 404
    return R.error(
        f'Endpoint /api/nias/{path} não encontrado',
        details='Consulte /api/nias/docs para lista completa de endpoints.'
    )


# ═══════════════════════════════════════════════════════════════════
# HANDLERS
# ═══════════════════════════════════════════════════════════════════

def _status():
    from flv.paths import get_storage_info
    storage = get_storage_info()
    return R.ok({
        'service': 'NIAS',
        'api': API_NAME,
        'version': API_VERSION,
        'timestamp': datetime.now().isoformat(),
        'storage': {
            'persistent': storage['persistent'],
            'type': storage['type'],
        },
        'scope': 'south_america',
        'scope_label': 'Inteligência Agrocomercial da América do Sul',
        'endpoints_count': 20,
    }, sources=['NIAS'], confidence='alta')


def _health():
    modules = {'server': 'ok'}
    try:
        from flv.db import get_conn
        get_conn().execute("SELECT 1")
        modules['database'] = 'ok'
    except Exception as e:
        modules['database'] = f'error: {e}'
    try:
        from flv.intelligence_engine import get_engine
        get_engine()
        modules['intelligence'] = 'ok'
    except Exception as e:
        modules['intelligence'] = f'error: {e}'
    try:
        from flv.climate_intelligence import get_climate_engine
        get_climate_engine()
        modules['climate'] = 'ok'
    except Exception as e:
        modules['climate'] = f'error: {e}'

    all_ok = all(v == 'ok' for v in modules.values())
    return R.ok({
        'healthy': all_ok,
        'modules': modules,
        'timestamp': datetime.now().isoformat(),
    }, sources=['NIAS'], confidence='alta')


# ─── PREÇOS ───────────────────────────────────────────────────────

def _prices_south_america(params: dict):
    import sqlite3
    from flv.paths import get_db_path
    from flv.sa_price_persistence import get_latest_sa_prices, get_sa_prices_summary, ensure_sa_prices_table

    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    ensure_sa_prices_table(conn)

    country = (params.get('country', ['']) or [''])[0].upper()
    product = (params.get('product', ['']) or [''])[0].lower()

    items   = get_latest_sa_prices(conn,
                                   country_code=country or None,
                                   product_normalized=product or None)
    summary = get_sa_prices_summary(conn)
    conn.close()

    if not items:
        return R.partial(
            {
                'scope':       'south_america',
                'country':     country or None,
                'items':       [],
                'db_summary':  summary,
            },
            'Preços sul-americanos ainda não populados. Execute o pipeline para coletar.',
            missing=['SA price collectors — execute /api/pipeline/run'],
            sources=['NIAS'],
        )

    return R.ok(
        {
            'scope':       'south_america',
            'country':     country or None,
            'product':     product or None,
            'items':       items,
            'total':       len(items),
            'db_summary':  summary,
            'note':        'Preços em moeda local. price_usd disponível quando conversão confiável.',
        },
        sources=['Open Market Sources', 'ODEPA', 'SIPSA', 'MIDAGRI', 'Mercado Central BA', 'Mercado Modelo UY'],
        confidence='media',
    )


def _prices_status():
    from flv.south_america_price_sources import get_status_summary
    import sqlite3
    from flv.paths import get_db_path
    from flv.sa_price_persistence import get_sa_prices_summary, ensure_sa_prices_table

    source_summary = get_status_summary()

    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    ensure_sa_prices_table(conn)
    db_summary = get_sa_prices_summary(conn)
    conn.close()

    return R.ok(
        {
            'scope':       'south_america',
            'sources':     source_summary,
            'db_summary':  db_summary,
            'br_note':     'Brasil gerenciado por CONAB/PROHORT via pipeline CEASA.',
        },
        sources=['NIAS'],
        confidence='alta',
    )


def _prices_sources():
    from flv.south_america_price_sources import SOUTH_AMERICA_PRICE_SOURCES
    out = {}
    for cc, cfg in SOUTH_AMERICA_PRICE_SOURCES.items():
        out[cc] = {
            'country':    cfg.get('name'),
            'currency':   cfg.get('currency'),
            'status':     cfg.get('status'),
            'products':   cfg.get('products', []),
            'sources': [
                {
                    'name':         s.get('name'),
                    'url':          s.get('url'),
                    'access_type':  s.get('access_type'),
                    'legal_status': s.get('legal_status'),
                    'frequency':    s.get('frequency'),
                    'status':       s.get('status'),
                    'implemented':  s.get('implemented', False),
                }
                for s in cfg.get('sources', [])
            ],
            'notes': cfg.get('notes', ''),
        }
    return R.ok(
        {'scope': 'south_america', 'countries': out, 'total': len(out)},
        sources=['NIAS'],
        confidence='alta',
    )


def _prices_latest(params: dict):
    # Rota SA: ?scope=south_america ou ?country= não-BR
    scope   = (params.get('scope',   ['']) or [''])[0]
    country = (params.get('country', ['']) or [''])[0].upper()
    if scope == 'south_america' or (country and country != 'BR'):
        return _prices_south_america(params)

    import sqlite3
    from flv.paths import get_db_path
    db = str(get_db_path())
    conn = sqlite3.connect(db, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row

    try:
        max_row = conn.execute("SELECT MAX(price_date) as d FROM flv_ceasa_prices").fetchone()
    except Exception:
        conn.close()
        return R.partial({'items': []}, 'Tabela de preços BR não disponível.', missing=['flv_ceasa_prices'])
    if not max_row or not max_row['d']:
        conn.close()
        return R.partial({'items': []}, 'Sem dados de preço no banco.', missing=['preços CEASA'])

    max_date = max_row['d']
    rows = conn.execute("""
        SELECT c.slug, c.name_pt as product, p.terminal as market,
               p.price_avg as price, p.price_min, p.price_max,
               c.unit, p.price_date as date, p.source,
               'CONAB/PROHORT' as api_source
        FROM flv_ceasa_prices p
        JOIN flv_cultures c ON c.id = p.culture_id
        WHERE p.price_date = ?
        ORDER BY c.name_pt, p.terminal
    """, (max_date,)).fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append({
            'product': r['product'],
            'slug': r['slug'],
            'market': r['market'] or 'Nacional',
            'price': round(r['price'], 2),
            'price_min': round(r['price_min'], 2) if r['price_min'] else None,
            'price_max': round(r['price_max'], 2) if r['price_max'] else None,
            'unit': r['unit'] or 'R$/kg',
            'date': r['date'],
            'source': r['api_source'],
            'confidence': 'alta',
        })

    return R.ok(
        {'items': items, 'total': len(items), 'date': max_date},
        sources=['CONAB/PROHORT'],
        confidence='alta',
    )


def _prices_history(params: dict):
    import sqlite3
    from flv.paths import get_db_path
    db = str(get_db_path())
    conn = sqlite3.connect(db, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row

    product = (params.get('product', ['']) or [''])[0]
    limit = int((params.get('limit', ['50']) or ['50'])[0])
    limit = min(limit, 200)

    query = """
        SELECT c.slug, c.name_pt as product, p.terminal as market,
               p.price_avg as price, c.unit, p.price_date as date
        FROM flv_ceasa_prices p
        JOIN flv_cultures c ON c.id = p.culture_id
    """
    args = []
    if product:
        query += " WHERE c.slug LIKE ? OR c.name_pt LIKE ?"
        args.extend([f'%{product}%', f'%{product}%'])
    query += " ORDER BY p.price_date DESC LIMIT ?"
    args.append(limit)

    rows = conn.execute(query, args).fetchall()
    conn.close()
    items = [dict(r) for r in rows]

    return R.ok(
        {'items': items, 'total': len(items)},
        sources=['CONAB/PROHORT'],
        confidence='alta',
    )


# ─── CLIMA ────────────────────────────────────────────────────────

def _weather_latest(params: dict):
    import sqlite3
    from flv.paths import get_db_path
    db = str(get_db_path())
    conn = sqlite3.connect(db, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row

    country = (params.get('country', ['']) or [''])[0].upper()
    scope   = (params.get('scope',   ['']) or [''])[0]

    # Rota SA: filtro por país ou scope=south_america
    if country or scope == 'south_america':
        from flv.sa_weather_persistence import get_latest_sa_weather, get_sa_weather_summary
        items = get_latest_sa_weather(conn, country_code=country or None)
        summary = get_sa_weather_summary(conn)
        conn.close()
        if not items:
            return R.partial(
                {'items': [], 'scope': 'south_america', 'country': country or None},
                'Dados climáticos sul-americanos ainda não foram populados pelo scheduler.',
                missing=['Open-Meteo SA batch'],
                sources=['NIAS'],
            )
        return R.ok(
            {
                'scope': 'south_america',
                'country': country or None,
                'items': items,
                'total': len(items),
                'date': summary.get('latest_date'),
                'countries_with_data': summary.get('countries'),
            },
            sources=['Open-Meteo'],
            confidence='alta',
        )

    # Rota padrão Brasil (mun_id based)
    max_row = conn.execute(
        "SELECT MAX(obs_date) as d FROM flv_climate WHERE mun_id IS NOT NULL"
    ).fetchone()
    if not max_row or not max_row['d']:
        conn.close()
        return R.partial({'items': []}, 'Sem dados climáticos no banco.', missing=['clima Open-Meteo'])

    max_date = max_row['d']
    rows = conn.execute("""
        SELECT mun_id, obs_date, temp_max_c, temp_min_c, precip_mm,
               wind_ms, humidity_pct, source
        FROM flv_climate
        WHERE obs_date = ? AND mun_id IS NOT NULL
        ORDER BY mun_id
    """, (max_date,)).fetchall()
    conn.close()

    items = []
    for r in rows:
        items.append({
            'region_id':   str(r['mun_id']),
            'date':        r['obs_date'],
            'temp_max_c':  r['temp_max_c'],
            'temp_min_c':  r['temp_min_c'],
            'precip_mm':   r['precip_mm'],
            'wind_kmh':    round((r['wind_ms'] or 0) * 3.6, 1),
            'humidity_pct': r['humidity_pct'],
            'source':      r['source'] or 'Open-Meteo',
        })

    return R.ok(
        {'items': items, 'total': len(items), 'date': max_date},
        sources=['Open-Meteo'],
        confidence='alta',
    )


def _weather_risk():
    from flv.climate_intelligence import get_climate_engine
    engine = get_climate_engine()
    events = engine.detect_extreme_events()
    alerts = engine.generate_climate_alerts()

    return R.ok(
        {
            'events': events,
            'alerts': alerts,
            'total_events': len(events),
            'total_alerts': len(alerts),
        },
        sources=['Open-Meteo', 'CONAB'],
        confidence='alta' if events else 'media',
    )


# ─── INTELIGÊNCIA ─────────────────────────────────────────────────

def _regions(params: dict):
    from flv.south_america_regions import get_all_regions, get_regions_by_country, summary, MONITORED_COUNTRIES
    country = (params.get('country', ['']) or [''])[0].upper()
    scope = (params.get('scope', ['']) or [''])[0]

    if country:
        regions = get_regions_by_country(country)
        return R.ok(
            {
                'scope': 'south_america',
                'country': country,
                'country_name': MONITORED_COUNTRIES.get(country, {}).get('name', country),
                'regions': regions,
                'total': len(regions),
            },
            sources=['NIAS'],
            confidence='alta',
        )

    regions = get_all_regions()
    meta = summary()
    return R.ok(
        {
            'scope': scope or 'south_america',
            'regions': regions,
            'total': meta['total_regions'],
            'countries': meta['countries'],
            'by_country': meta['by_country'],
            'monitored_countries': meta['monitored_countries'],
        },
        sources=['NIAS'],
        confidence='alta',
    )


def _weather_south_america():
    import sqlite3
    from flv.paths import get_db_path
    from flv.sa_weather_persistence import get_latest_sa_weather, get_sa_weather_summary

    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row

    # 1. Tentar dados persistidos no banco (fonte primária)
    items = get_latest_sa_weather(conn)
    summary = get_sa_weather_summary(conn)
    conn.close()

    if items:
        return R.ok(
            {
                'scope':             'south_america',
                'items':             items,
                'total':             len(items),
                'date':              summary.get('latest_date'),
                'countries_covered': summary.get('countries'),
                'source_mode':       'persisted_db',
            },
            sources=['Open-Meteo'],
            confidence='alta',
        )

    # 2. Fallback: buscar do in-memory cache Open-Meteo (sem persistir agora)
    from flv.openmeteo_batch_sa import fetch_south_america_weather, get_cache_status
    cache_st = get_cache_status()
    result = fetch_south_america_weather()
    status  = result.get('status', 'error')

    if status == 'rate_limited':
        return R.partial(
            {'items': result.get('results', []), 'scope': 'south_america'},
            'Open-Meteo com rate limit ativo. Banco ainda não populado.',
            missing=['Open-Meteo live', 'scheduler run'],
            sources=['Open-Meteo (cache)'],
        )
    if status == 'error':
        return R.partial(
            {'items': [], 'scope': 'south_america'},
            result.get('message', 'Erro ao buscar dados climáticos. Execute o pipeline.'),
            missing=['Open-Meteo', 'scheduler run'],
        )

    return R.ok(
        {
            'scope':       'south_america',
            'items':       result.get('results', []),
            'total':       result.get('total_points', 0),
            'fetched_at':  result.get('fetched_at'),
            'source_mode': 'in_memory_cache',
            'note':        'Dados em memória — rode o pipeline para persistir no banco.',
        },
        sources=['Open-Meteo'],
        confidence='media',
    )


def _intelligence_weather_price(params: dict = None):
    if params is None:
        params = {}
    scope   = (params.get('scope',   ['']) or [''])[0]
    country = (params.get('country', ['']) or [''])[0].upper()

    # Rota sul-americana: usa dados climáticos do banco + lógica de impacto regional
    if scope == 'south_america' or (country and country != 'BR'):
        return _intelligence_weather_price_sa(country=country or None)

    # Rota padrão Brasil
    from flv.climate_intelligence import get_climate_engine
    engine = get_climate_engine()
    engine.detect_extreme_events()
    result = engine.analyze_weather_price_correlation()

    mode = result.get('mode', 'real_data')
    if mode == 'insufficient_data':
        return R.partial(
            {'items': result.get('items', [])},
            result.get('message', 'Dados insuficientes.'),
            missing=result.get('missing', []),
            sources=['Open-Meteo', 'CONAB/PROHORT'],
        )

    return R.ok(
        {
            'scope':        scope or 'brazil',
            'country':      country or 'BR',
            'items':        result.get('items', []),
            'total':        len(result.get('items', [])),
            'data_quality': result.get('data_quality', {}),
        },
        mode=mode,
        sources=['Open-Meteo', 'CONAB/PROHORT'],
        confidence='media',
    )


def _intelligence_weather_price_sa(country: str | None = None):
    """
    Inteligência clima × preço para América do Sul.
    Usa dados climáticos persistidos no banco.
    Se não houver preço local, gera análise climática honesta sem inventar preço.
    """
    import sqlite3
    from flv.paths import get_db_path
    from flv.sa_weather_persistence import get_latest_sa_weather

    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row

    weather_items = get_latest_sa_weather(conn, country_code=country)
    conn.close()

    if not weather_items:
        return R.partial(
            {'items': [], 'scope': 'south_america', 'country': country},
            'Dados climáticos sul-americanos ainda não foram populados pelo scheduler.',
            missing=['Open-Meteo SA batch — execute /api/pipeline/run'],
            sources=['NIAS'],
        )

    # Gerar sinais climáticos por polo
    items = []
    for w in weather_items:
        signals = []
        confidence = 'media'

        temp_max  = w.get('temp_max_c')
        temp_min  = w.get('temp_min_c')
        precip    = w.get('precip_mm', 0) or 0
        region    = w.get('region_name', '')
        cc        = w.get('country_code', '')

        if temp_max and temp_max > 36:
            signals.append('calor extremo')
            confidence = 'media'
        if temp_min and temp_min < 2:
            signals.append('risco de geada')
            confidence = 'alta'
        if precip > 30:
            signals.append('chuva intensa')
        if precip == 0 and temp_max and temp_max > 30:
            signals.append('déficit hídrico')

        weather_signal = ' + '.join(signals) if signals else 'condições normais'
        has_risk       = bool(signals and signals != ['condições normais'])

        items.append({
            'country':             cc,
            'region':              region,
            'region_id':           w.get('region_id'),
            'lat':                 w.get('lat'),
            'lon':                 w.get('lon'),
            'obs_date':            w.get('obs_date'),
            'weather_signal':      weather_signal,
            'price_signal':        'sem preço local persistido',
            'expected_impact':     'risco de pressão regional' if has_risk else 'sem impacto climático imediato',
            'confidence':          confidence if has_risk else 'baixa',
            'explanation': (
                f'Sinal climático em {region} ({cc}): {weather_signal}. '
                'Preço local sul-americano ainda não está disponível no banco — '
                'impacto comercial deve ser monitorado via fontes oficiais locais.'
            ) if has_risk else (
                f'{region} ({cc}) sem eventos climáticos extremos no momento.'
            ),
            'recommended_action': (
                f'Monitorar oferta de {cc} e verificar fonte oficial de preço local.' if has_risk
                else 'Sem ação imediata necessária.'
            ),
            'temp_max_c':  temp_max,
            'temp_min_c':  temp_min,
            'precip_mm':   precip,
            'source':      w.get('source', 'Open-Meteo'),
            'scope':       'south_america',
        })

    # Ordenar: regiões com risco primeiro
    items.sort(key=lambda x: (0 if x['weather_signal'] != 'condições normais' else 1, x['country']))

    return R.ok(
        {
            'scope':   'south_america',
            'country': country,
            'items':   items,
            'total':   len(items),
            'note':    'Análise baseada em clima real. Preço local por país pendente de fonte oficial.',
        },
        mode='real_weather_no_price',
        sources=['Open-Meteo'],
        confidence='media',
    )


def _intelligence_opportunities():
    from flv.intelligence_engine import get_engine
    engine = get_engine()
    opps = engine.generate_opportunities()
    return R.ok(
        {'opportunities': opps, 'total': len(opps)},
        sources=['CONAB', 'Open-Meteo', 'NewsAPI'],
        confidence='media',
    )


def _intelligence_predictions():
    from flv.intelligence_engine import get_engine
    engine = get_engine()
    preds = engine.generate_predictions()
    return R.ok(
        {'predictions': preds, 'total': len(preds)},
        sources=['CONAB', 'Open-Meteo'],
        confidence='media',
    )


def _intelligence_alerts():
    from flv.intelligence_engine import get_engine
    engine = get_engine()
    alerts = engine.generate_alerts()
    return R.ok(
        {'alerts': alerts, 'total': len(alerts)},
        sources=['CONAB', 'Open-Meteo', 'NewsAPI'],
        confidence='media',
    )


# ─── RELATÓRIO ────────────────────────────────────────────────────

def _report_daily():
    from flv.intelligence_engine import get_engine
    engine = get_engine()
    report = engine.generate_executive_report()
    return R.ok(
        report,
        sources=['CONAB', 'Open-Meteo', 'NewsAPI', 'BCB'],
        confidence=report.get('confianca_geral', 'media'),
    )


# ─── FONTES ───────────────────────────────────────────────────────

def _sources_status():
    from flv.intelligence_engine import get_engine
    from flv.climapi_client import get_climapi_status
    from flv.paths import get_storage_info

    engine = get_engine()
    freshness = engine.get_data_freshness()
    climapi = get_climapi_status()
    storage = get_storage_info()

    sources = {
        'conab': {
            'status': freshness['source_status'].get('ceasa', 'fallback'),
            'last_success': freshness.get('last_price_update'),
            'description': 'CONAB/CEASA Preços',
        },
        'cepea': {
            'status': 'fallback',
            'reason': 'Sem API pública oficial. WAF bloqueia scraping.',
            'replacement': 'CONAB/PROHORT',
        },
        'climapi': {
            'status': climapi.get('status', 'fallback'),
            'credentials_present': climapi.get('credentials_present', False),
            'replacement': 'Open-Meteo',
        },
        'open_meteo': {
            'status': freshness['source_status'].get('open_meteo', 'fallback'),
            'last_success': freshness.get('last_weather_update'),
            'description': 'Open-Meteo Clima',
        },
        'news': {
            'status': freshness['source_status'].get('news', 'fallback'),
            'last_success': freshness.get('last_news_update'),
        },
        'macro': {
            'status': freshness['source_status'].get('macro', 'fallback'),
            'last_success': freshness.get('last_macro_update'),
        },
    }

    return R.ok(
        {'sources': sources, 'storage': storage},
        sources=['NIAS'],
        confidence='alta',
    )


# ─── PIPELINE ─────────────────────────────────────────────────────

def _pipeline_status():
    from flv.scheduler import get_pipeline_status
    status = get_pipeline_status()
    return R.ok(status, sources=['NIAS'], confidence='alta')


def _pipeline_freshness():
    from flv.scheduler import get_pipeline_freshness
    freshness = get_pipeline_freshness()
    return R.ok(freshness, sources=['NIAS'], confidence='alta')


def _pipeline_runs():
    from flv.scheduler import get_pipeline_runs
    runs = get_pipeline_runs(20)
    return R.ok(
        {'runs': runs, 'total': len(runs)},
        sources=['NIAS'],
        confidence='alta',
    )


# ─── DOCUMENTAÇÃO ─────────────────────────────────────────────────


# ─── ADVISOR (Conselheiro NIAS) ───────────────────────────────────

def _advisor_conn():
    import sqlite3
    from flv.paths import get_db_path
    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        from flv.db_migration import ensure_runtime_schema
        ensure_runtime_schema(conn)
    except Exception:
        pass
    return conn


def _advisor_recommendations(params: dict):
    conn = _advisor_conn()
    try:
        from flv.advisor_engine import get_advisor
        engine = get_advisor(conn)
        advices = engine.generate_advice()
        for a in advices:
            a['explicacao_completa'] = engine.explain_recommendation(a)
    finally:
        conn.close()

    return R.ok(
        {
            'scope':           'south_america',
            'recommendations': advices,
            'total':           len(advices),
            'note': (
                'Recomendações geradas a partir de dados reais de clima e preços. '
                'Cada conselho inclui justificativa, cenário contrário e nível de confiança.'
            ),
        },
        sources=['Open-Meteo', 'CONAB/PROHORT'],
        confidence='media',
    )


def _advisor_summary():
    conn = _advisor_conn()
    try:
        from flv.advisor_engine import get_advisor
        engine  = get_advisor(conn)
        summary = engine.generate_executive_summary()
    finally:
        conn.close()

    return R.ok(
        summary,
        sources=['Open-Meteo', 'CONAB/PROHORT'],
        confidence=summary.get('confianca', 'media'),
    )


def _advisor_opportunities():
    conn = _advisor_conn()
    try:
        from flv.advisor_engine import get_advisor
        engine = get_advisor(conn)
        opps   = engine.rank_opportunities()
        for o in opps:
            o['explicacao_completa'] = engine.explain_recommendation(o)
    finally:
        conn.close()

    return R.ok(
        {
            'scope':         'south_america',
            'opportunities': opps,
            'total':         len(opps),
        },
        sources=['Open-Meteo', 'CONAB/PROHORT'],
        confidence='media',
    )


def _advisor_risks():
    conn = _advisor_conn()
    try:
        from flv.advisor_engine import get_advisor
        engine  = get_advisor(conn)
        advices = engine.generate_advice()
        risks   = [
            a for a in advices
            if a.get('tipo') == 'alerta'
            or any(s in a.get('sinais_climaticos', [])
                   for s in ['risco de geada', 'calor extremo', 'chuva muito intensa'])
        ]
    finally:
        conn.close()

    return R.ok(
        {
            'scope': 'south_america',
            'risks': risks,
            'total': len(risks),
        },
        sources=['Open-Meteo'],
        confidence='alta' if risks else 'media',
    )


def _advisor_thesis(params: dict):
    product = (params.get('product', ['']) or [''])[0]
    region  = (params.get('region',  ['']) or [''])[0]
    if not product and not region:
        return R.error(
            'Informe ao menos ?product= ou ?region=',
            details='Exemplo: /api/nias/advisor/thesis?product=tomate&region=Sul+de+Minas'
        )

    conn = _advisor_conn()
    try:
        from flv.advisor_engine import get_advisor
        engine = get_advisor(conn)
        thesis = engine.build_investment_thesis(
            product=product or 'produto',
            region=region  or 'brasil',
        )
    finally:
        conn.close()

    return R.ok(
        thesis,
        sources=['CONAB/PROHORT', 'Open-Meteo'],
        confidence=thesis.get('score', {}).get('confianca', 'media'),
    )


def _advisor_product(params: dict):
    product = (params.get('product', ['']) or [''])[0]
    if not product:
        return R.error('Informe ?product=nome', details='Exemplo: /api/nias/advisor/product?product=tomate')

    conn = _advisor_conn()
    try:
        from flv.advisor_engine import get_advisor
        engine  = get_advisor(conn)
        advices = engine.generate_advice()
        product_l = product.lower()
        filtered = [
            a for a in advices
            if product_l in (a.get('produto') or '').lower()
            or product_l in (a.get('slug') or '').lower()
        ]
        for a in filtered:
            a['explicacao_completa'] = engine.explain_recommendation(a)
    finally:
        conn.close()

    return R.ok(
        {
            'produto':         product,
            'scope':           'south_america',
            'recommendations': filtered,
            'total':           len(filtered),
        },
        sources=['CONAB/PROHORT', 'Open-Meteo'],
        confidence='media',
    )


def _advisor_country(params: dict):
    country = (params.get('country', ['']) or [''])[0].upper()
    if not country:
        return R.error('Informe ?country=XX', details='Exemplo: /api/nias/advisor/country?country=AR')

    conn = _advisor_conn()
    try:
        from flv.advisor_engine import get_advisor
        engine  = get_advisor(conn)
        advices = engine.generate_advice()
        filtered = [a for a in advices if a.get('pais') == country]
        for a in filtered:
            a['explicacao_completa'] = engine.explain_recommendation(a)
        summary = engine.generate_executive_summary()
    finally:
        conn.close()

    return R.ok(
        {
            'pais':            country,
            'scope':           'south_america',
            'recommendations': filtered,
            'total':           len(filtered),
            'resumo':          summary.get('resumo', ''),
        },
        sources=['Open-Meteo', 'CONAB/PROHORT'],
        confidence='media',
    )


def _advisor_region(params: dict):
    region = (params.get('region', ['']) or [''])[0]
    if not region:
        return R.error('Informe ?region=nome', details='Exemplo: /api/nias/advisor/region?region=Mendoza')

    conn = _advisor_conn()
    try:
        from flv.advisor_engine import get_advisor
        engine  = get_advisor(conn)
        advices = engine.generate_advice()
        region_l = region.lower()
        filtered = [
            a for a in advices
            if region_l in (a.get('regiao') or '').lower()
        ]
        for a in filtered:
            a['explicacao_completa'] = engine.explain_recommendation(a)
    finally:
        conn.close()

    return R.ok(
        {
            'regiao':          region,
            'scope':           'south_america',
            'recommendations': filtered,
            'total':           len(filtered),
        },
        sources=['Open-Meteo', 'CONAB/PROHORT'],
        confidence='media',
    )


# ─── BRAIN (Cérebro NIAS) ─────────────────────────────────────────

def _brain_conn():
    import sqlite3
    from flv.paths import get_db_path
    conn = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        from flv.db_migration import ensure_runtime_schema
        ensure_runtime_schema(conn)
    except Exception:
        pass
    return conn


def _brain_pulse():
    conn = _brain_conn()
    try:
        from flv.brain_engine import get_brain
        engine = get_brain(conn)
        pulse  = engine.generate_system_pulse()
    finally:
        conn.close()
    return R.ok(pulse, sources=['NIAS Brain'], confidence='alta')


def _brain_events(params: dict):
    conn = _brain_conn()
    try:
        from flv.brain_engine import get_brain
        engine = get_brain(conn)
        events = engine.generate_live_events()
        country = (params.get('country', ['']) or [''])[0].upper()
        if country:
            events = [e for e in events if e.get('pais') == country]
        gravity = (params.get('gravity', ['']) or [''])[0]
        if gravity:
            events = [e for e in events if e.get('gravidade') == gravity]
    finally:
        conn.close()

    return R.ok(
        {
            'events': events,
            'total':  len(events),
            'country': country if country else None,
            'timestamp': datetime.now().isoformat(),
        },
        sources=['Open-Meteo', 'NIAS SA Prices'],
        confidence='alta' if events else 'media',
    )


def _brain_decisions(params: dict):
    conn = _brain_conn()
    try:
        from flv.brain_engine import get_brain
        engine  = get_brain(conn)
        cards   = engine.generate_decision_cards()
        country = (params.get('country', ['']) or [''])[0].upper()
        tipo    = (params.get('tipo',    ['']) or [''])[0]
        if country:
            cards = [c for c in cards if c.get('pais') == country]
        if tipo:
            cards = [c for c in cards if c.get('tipo') == tipo]
    finally:
        conn.close()

    return R.ok(
        {
            'decisions': cards,
            'total':     len(cards),
            'country':   country if country else None,
            'tipo':      tipo if tipo else None,
            'timestamp': datetime.now().isoformat(),
            'note': (
                'Cada decisão inclui validade e gatilhos de invalidação. '
                'Tipo "monitorar" indica ausência de preço local — não é recomendação de ação.'
            ),
        },
        sources=['Open-Meteo', 'CONAB/PROHORT', 'NIAS SA Prices'],
        confidence='media',
    )


def _brain_radar():
    conn = _brain_conn()
    try:
        from flv.brain_engine import get_brain
        engine = get_brain(conn)
        radar  = engine.generate_temporal_radar()
    finally:
        conn.close()
    return R.ok(radar, sources=['Open-Meteo', 'NIAS Brain'], confidence='media')


def _brain_thesis(params: dict):
    product = (params.get('product', ['']) or [''])[0]
    country = (params.get('country', ['']) or [''])[0].upper()
    region  = (params.get('region',  ['']) or [''])[0]

    conn = _brain_conn()
    try:
        from flv.brain_engine import get_brain
        engine = get_brain(conn)
        thesis = engine.generate_thesis(product=product, country=country, region=region)
    finally:
        conn.close()

    conf = 'alta' if thesis.get('has_price') and thesis.get('has_climate') else 'media'
    return R.ok(thesis, sources=thesis.get('fontes', ['NIAS Brain']), confidence=conf)


def _brain_quality():
    conn = _brain_conn()
    try:
        from flv.brain_engine import get_brain
        engine  = get_brain(conn)
        quality = engine.evaluate_data_quality()
        changes = engine.detect_changes()
    finally:
        conn.close()
    return R.ok(
        {'quality': quality, 'changes': changes, 'timestamp': datetime.now().isoformat()},
        sources=['NIAS Brain'],
        confidence='alta',
    )


def _brain_summary():
    conn = _brain_conn()
    try:
        from flv.brain_engine import get_brain
        engine  = get_brain(conn)
        pulse   = engine.generate_system_pulse()
        events  = engine.generate_live_events()
        cards   = engine.generate_decision_cards()
        changes = engine.detect_changes()
        quality = engine.evaluate_data_quality()
    finally:
        conn.close()

    n_crit = sum(1 for e in events if e.get('gravidade') == 'critica')
    n_high = sum(1 for e in events if e.get('gravidade') == 'alta')

    return R.ok(
        {
            'scope':          'south_america',
            'health':         pulse['health'],
            'timestamp':      datetime.now().isoformat(),
            'pulse':          pulse,
            'events_summary': {
                'total':     len(events),
                'criticos':  n_crit,
                'altos':     n_high,
                'top3':      events[:3],
            },
            'decisions_summary': {
                'total':   len(cards),
                'alertas': sum(1 for c in cards if c.get('tipo') == 'alerta'),
                'comprar': sum(1 for c in cards if c.get('tipo') in ('comprar', 'antecipar_compra')),
                'monitorar': sum(1 for c in cards if c.get('tipo') == 'monitorar'),
                'top3':    cards[:3],
            },
            'changes':  changes,
            'quality':  quality,
            'note': (
                'Resumo do Cérebro NIAS. Todos os dados são reais — sem projeções inventadas. '
                'Para análise detalhada: /api/nias/brain/events, /decisions, /radar, /thesis.'
            ),
        },
        sources=['Open-Meteo', 'CONAB/PROHORT', 'NIAS SA Prices'],
        confidence=pulse.get('sources', {}).get('clima_sa', {}).get('status', 'media'),
    )


def _brain_command(body: dict):
    command = (body.get('command') or body.get('cmd') or '').strip()
    if not command:
        return R.error(
            'Informe o campo "command" no body JSON.',
            details='Exemplo: {"command": "alerta AR"} ou {"command": "tese tomate CL"}'
        )
    conn = _brain_conn()
    try:
        from flv.brain_engine import get_brain
        engine = get_brain(conn)
        result = engine.process_command(command)
    finally:
        conn.close()
    return R.ok(result, sources=['NIAS Brain'], confidence='media')


def _docs():
    endpoints = [
        {'path': '/api/nias/status', 'method': 'GET', 'description': 'Status geral da API', 'legacy': None},
        {'path': '/api/nias/health', 'method': 'GET', 'description': 'Health check com módulos', 'legacy': '/api/health'},
        {'path': '/api/nias/regions', 'method': 'GET', 'description': 'Regiões monitoradas da América do Sul', 'params': '?country=BR|AR|CL|PE|BO|PY|UY|CO|EC'},
        {'path': '/api/nias/regions/south-america', 'method': 'GET', 'description': 'Alias: todos os polos sul-americanos'},
        {'path': '/api/nias/prices/latest', 'method': 'GET', 'description': 'Preços mais recentes por produto/mercado', 'params': '?country=BR'},
        {'path': '/api/nias/prices/history', 'method': 'GET', 'description': 'Histórico de preços', 'params': '?product=tomate&limit=50'},
        {'path': '/api/nias/weather/latest', 'method': 'GET', 'description': 'Dados climáticos mais recentes', 'params': '?country=BR'},
        {'path': '/api/nias/weather/south-america', 'method': 'GET', 'description': 'Clima em batch para todos os polos sul-americanos (Open-Meteo)'},
        {'path': '/api/nias/weather/risk', 'method': 'GET', 'description': 'Riscos climáticos e alertas', 'legacy': '/api/climate/alerts'},
        {'path': '/api/nias/intelligence/weather-price', 'method': 'GET', 'description': 'Correlação clima × preço', 'params': '?country=BR&scope=south_america'},
        {'path': '/api/nias/intelligence/opportunities', 'method': 'GET', 'description': 'Oportunidades de mercado', 'legacy': '/api/intelligence/opportunities'},
        {'path': '/api/nias/intelligence/predictions', 'method': 'GET', 'description': 'Previsões de preço', 'legacy': '/api/intelligence/predictions'},
        {'path': '/api/nias/intelligence/alerts', 'method': 'GET', 'description': 'Alertas acionáveis', 'legacy': '/api/intelligence/alerts'},
        {'path': '/api/nias/report/daily', 'method': 'GET', 'description': 'Relatório executivo diário', 'legacy': '/api/intelligence/report'},
        {'path': '/api/nias/sources/status', 'method': 'GET', 'description': 'Status de todas as fontes de dados', 'legacy': '/api/sources/status'},
        {'path': '/api/nias/pipeline/status', 'method': 'GET', 'description': 'Status do pipeline', 'legacy': '/api/pipeline/status'},
        {'path': '/api/nias/pipeline/freshness', 'method': 'GET', 'description': 'Freshness dos dados', 'legacy': '/api/pipeline/freshness'},
        {'path': '/api/nias/pipeline/runs', 'method': 'GET', 'description': 'Histórico de execuções do pipeline', 'legacy': '/api/pipeline/runs'},
        {'path': '/api/nias/docs', 'method': 'GET', 'description': 'Esta documentação', 'legacy': None},
    ]

    return R.ok(
        {
            'title': 'NIAS API Core v1',
            'description': 'API oficial do NIAS — Inteligência Agrocomercial da América do Sul.',
            'scope': 'south_america',
            'scope_label': 'América do Sul',
            'base_url': '/api/nias',
            'response_format': {
                'success': '{ status: "ok", api, version, mode, data, meta: { sources, updated_at, confidence } }',
                'error': '{ status: "error", api, version, message, details }',
                'partial': '{ status: "partial", api, version, mode: "insufficient_data", message, missing, data, meta }',
            },
            'modes': ['real_data', 'partial', 'fallback', 'insufficient_data'],
            'endpoints': endpoints,
            'total_endpoints': len(endpoints),
        },
        sources=['NIAS'],
        confidence='alta',
    )
