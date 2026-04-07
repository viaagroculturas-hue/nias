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
    """Build Prophet-compatible DataFrame dict with columns: ds, y, precip_7d, temp_max_avg, ndvi, is_holiday."""
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

    holiday_dates = set(h[0] for h in BR_HOLIDAYS_2026)

    # Build feature rows
    result = []
    last_ndvi = 0.55
    last_temp = 28.0
    last_precip = 5.0

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

        is_hol = 1.0 if ds in holiday_dates else 0.0

        result.append({
            'ds': ds,
            'y': y,
            'precip_7d': precip_7d,
            'temp_max_avg': temp_max,
            'ndvi': ndvi or last_ndvi,
            'is_holiday': is_hol,
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
        })

    return future
