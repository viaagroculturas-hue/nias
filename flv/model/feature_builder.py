"""FLV Feature Builder — Assembles feature matrix for Prophet from DB tables."""
import time, re
from datetime import datetime, timedelta

def _parse_date(ds):
    """Parse various date formats from CONAB/CEASA: 'YYYY-MM-DD', 'DD-MM-YYYY', 'DD-MM-YYYY - DD-MM-YYYY'."""
    if not ds:
        return None
    ds = ds.strip()
    # Range format: take the start date
    if ' - ' in ds:
        ds = ds.split(' - ')[0].strip()
    # Try YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', ds):
        return ds
    # Try DD-MM-YYYY or DD/MM/YYYY
    m = re.match(r'^(\d{2})[-/](\d{2})[-/](\d{4})$', ds)
    if m:
        return f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
    return None

def build_features(culture_slug, terminal=None, mun_id=None, days=120):
    """Build Prophet-compatible DataFrame dict with columns: ds, y, local_clima, macro_*, news_risk_index, teleconnections_*."""
    from flv.db import get_conn
    from flv.model.thresholds import BR_HOLIDAYS_2026
    conn = get_conn()

    cid = conn.execute("SELECT id FROM flv_cultures WHERE slug=?", (culture_slug,)).fetchone()
    if not cid:
        return []

    # Get price series
    price_sql = "SELECT price_date as ds, price_avg as y FROM flv_ceasa_prices WHERE culture_id=?"
    params = [cid['id']]
    if terminal:
        price_sql += " AND terminal=?"
        params.append(terminal)
    price_sql += " ORDER BY price_date DESC LIMIT ?"
    params.append(days)

    prices = conn.execute(price_sql, params).fetchall()
    if not prices:
        return []

    prices = list(reversed([dict(r) for r in prices]))

    # Get climate data (average across all tracked municipalities if mun_id not specified)
    climate_sql = """
        SELECT obs_date, AVG(temp_max_c) as temp_max, AVG(precip_mm) as precip
        FROM flv_climate
        WHERE obs_date >= ? GROUP BY obs_date ORDER BY obs_date
    """
    min_date = prices[0]['ds'] if prices else '2020-01-01'
    climate_rows = conn.execute(climate_sql, (min_date,)).fetchall()
    climate_map = {r['obs_date']: dict(r) for r in climate_rows}

    # Get NDVI data
    ndvi_sql = "SELECT obs_date, AVG(ndvi_value) as ndvi FROM flv_ndvi WHERE obs_date >= ? GROUP BY obs_date ORDER BY obs_date"
    ndvi_rows = conn.execute(ndvi_sql, (min_date,)).fetchall()
    ndvi_map = {r['obs_date']: r['ndvi'] for r in ndvi_rows}

    # Get macro indicators (economia/energia) — JOIN por ds
    macro_sql = """
        SELECT obs_date, diesel_brl_l, diesel_change_pct,
               brent_usd, brent_change_pct, wti_usd, wti_change_pct,
               usd_brl, selic_pct, ipca_yoy_pct
        FROM flv_macro_indicators
        WHERE obs_date >= ?
        ORDER BY obs_date
    """
    try:
        macro_rows = conn.execute(macro_sql, (min_date,)).fetchall()
        macro_map = {r['obs_date']: dict(r) for r in macro_rows}
    except Exception:
        macro_map = {}

    # Notícias: risco diário agregado
    news_sql = """
        SELECT obs_date, risk_index
        FROM flv_news_risk_daily
        WHERE obs_date >= ?
        ORDER BY obs_date
    """
    try:
        news_rows = conn.execute(news_sql, (min_date,)).fetchall()
        news_map = {r['obs_date']: float(r['risk_index']) for r in news_rows}
    except Exception:
        news_map = {}

    # Teleconexões: ONI e Atlântico Norte
    glob_sql = """
        SELECT obs_date, oni, atl_north_warm_idx
        FROM flv_global_climate
        WHERE obs_date >= ?
        ORDER BY obs_date
    """
    try:
        glob_rows = conn.execute(glob_sql, (min_date,)).fetchall()
        glob_map = {r['obs_date']: dict(r) for r in glob_rows}
    except Exception:
        glob_map = {}

    holiday_dates = set(h[0] for h in BR_HOLIDAYS_2026)

    # Build feature rows
    result = []
    last_ndvi = 0.55
    last_temp = 28.0
    last_precip = 5.0
    last_usd = 5.0
    last_selic = 10.0
    last_ipca = 4.0
    last_diesel = 6.0
    last_diesel_chg = 0.0
    last_brent = 80.0
    last_brent_chg = 0.0
    last_wti = 75.0
    last_wti_chg = 0.0
    last_news_risk = 0.0
    last_oni = 0.0
    last_atl = 0.0

    for p in prices:
        ds = _parse_date(p['ds'])
        if not ds:
            continue
        y = p['y']
        if y is None or y <= 0:
            continue

        # Climate: 7-day rolling average
        clim = climate_map.get(ds)
        temp_max = clim['temp_max'] if clim and clim['temp_max'] else last_temp
        precip = clim['precip'] if clim and clim['precip'] is not None else last_precip
        last_temp = temp_max
        last_precip = precip

        # 7-day rolling precip sum (approximate)
        precip_7d = precip * 7  # simplified; real impl would sum 7 days

        # NDVI (use nearest available)
        ndvi = ndvi_map.get(ds, last_ndvi)
        if ndvi:
            last_ndvi = ndvi

        macro = macro_map.get(ds) or {}
        usd_brl = macro.get('usd_brl')
        selic_pct = macro.get('selic_pct')
        ipca_yoy_pct = macro.get('ipca_yoy_pct')
        diesel_brl_l = macro.get('diesel_brl_l')
        diesel_change_pct = macro.get('diesel_change_pct')
        brent_usd = macro.get('brent_usd')
        brent_change_pct = macro.get('brent_change_pct')
        wti_usd = macro.get('wti_usd')
        wti_change_pct = macro.get('wti_change_pct')

        if usd_brl is not None:
            last_usd = usd_brl
        if selic_pct is not None:
            last_selic = selic_pct
        if ipca_yoy_pct is not None:
            last_ipca = ipca_yoy_pct
        if diesel_brl_l is not None:
            last_diesel = diesel_brl_l
        if diesel_change_pct is not None:
            last_diesel_chg = diesel_change_pct
        if brent_usd is not None:
            last_brent = brent_usd
        if brent_change_pct is not None:
            last_brent_chg = brent_change_pct
        if wti_usd is not None:
            last_wti = wti_usd
        if wti_change_pct is not None:
            last_wti_chg = wti_change_pct

        news_risk = news_map.get(ds)
        if news_risk is not None:
            last_news_risk = float(news_risk)

        glob = glob_map.get(ds) or {}
        oni = glob.get('oni')
        atl = glob.get('atl_north_warm_idx')
        if oni is not None:
            last_oni = oni
        if atl is not None:
            last_atl = atl

        is_hol = 1.0 if ds in holiday_dates else 0.0

        result.append({
            'ds': ds,
            'y': y,
            'precip_7d': precip_7d,
            'temp_max_avg': temp_max,
            'ndvi': ndvi or last_ndvi,
            'is_holiday': is_hol,
            'usd_brl': usd_brl if usd_brl is not None else last_usd,
            'selic_pct': selic_pct if selic_pct is not None else last_selic,
            'ipca_yoy_pct': ipca_yoy_pct if ipca_yoy_pct is not None else last_ipca,
            'diesel_brl_l': diesel_brl_l if diesel_brl_l is not None else last_diesel,
            'diesel_change_pct': diesel_change_pct if diesel_change_pct is not None else last_diesel_chg,
            'brent_usd': brent_usd if brent_usd is not None else last_brent,
            'brent_change_pct': brent_change_pct if brent_change_pct is not None else last_brent_chg,
            'wti_usd': wti_usd if wti_usd is not None else last_wti,
            'wti_change_pct': wti_change_pct if wti_change_pct is not None else last_wti_chg,
            'news_risk_index': news_risk if news_risk is not None else last_news_risk,
            'oni': oni if oni is not None else last_oni,
            'atl_north_warm_idx': atl if atl is not None else last_atl,
        })

    return result

def build_future_regressors(last_features, horizon=15):
    """Build regressor values for future dates (days 1-15)."""
    if not last_features:
        return []

    last = last_features[-1]
    base_date = datetime.strptime(last['ds'], '%Y-%m-%d')
    from flv.model.thresholds import BR_HOLIDAYS_2026
    holiday_dates = set(h[0] for h in BR_HOLIDAYS_2026)

    future = []
    for i in range(1, horizon + 1):
        dt = base_date + timedelta(days=i)
        ds = dt.strftime('%Y-%m-%d')
        future.append({
            'ds': ds,
            'precip_7d': last['precip_7d'],      # persistence
            'temp_max_avg': last['temp_max_avg'],  # persistence
            'ndvi': last['ndvi'],                  # slow-changing
            'is_holiday': 1.0 if ds in holiday_dates else 0.0,
            'usd_brl': last.get('usd_brl', 5.0),
            'selic_pct': last.get('selic_pct', 10.0),
            'ipca_yoy_pct': last.get('ipca_yoy_pct', 4.0),
            'diesel_brl_l': last.get('diesel_brl_l', 6.0),
            'diesel_change_pct': last.get('diesel_change_pct', 0.0),
            'brent_usd': last.get('brent_usd', 80.0),
            'brent_change_pct': last.get('brent_change_pct', 0.0),
            'wti_usd': last.get('wti_usd', 75.0),
            'wti_change_pct': last.get('wti_change_pct', 0.0),
            'news_risk_index': last.get('news_risk_index', 0.0),
            'oni': last.get('oni', 0.0),
            'atl_north_warm_idx': last.get('atl_north_warm_idx', 0.0),
        })

    return future
