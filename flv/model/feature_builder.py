"""FLV Feature Builder — Assembles feature matrix for Prophet from DB tables."""
import math, time, re
from datetime import datetime, timedelta

RJ_STATUS_WEIGHTS = {
    'falencia': 1.0,
    'em_recuperacao': 0.85,
    'recuperacao_aprovada': 0.45,
    'reorganizado': 0.25,
}


def _clamp(value, low=0.0, high=1.0):
    return max(low, min(high, float(value)))


def _safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _haversine_km(lat1, lon1, lat2, lon2):
    """Distance between two coordinate pairs in kilometers."""
    radius_km = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * radius_km * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _fetch_target_municipalities(conn, culture, terminal=None, mun_id=None):
    """Select the production cluster used to geo-cross climate and legal stress."""
    params = []
    where = []
    if mun_id:
        where.append("id=?")
        params.append(mun_id)
    elif terminal:
        where.append("ceasa_ref=?")
        params.append(terminal)

    if where:
        rows = conn.execute(
            f"SELECT id, name, state_uf, lat, lon FROM flv_municipalities WHERE {' AND '.join(where)}",
            params,
        ).fetchall()
        if rows:
            return [dict(r) for r in rows]

    main_producers = [uf.strip().upper() for uf in (culture.get('main_producers') or '').split(',') if uf.strip()]
    if main_producers:
        placeholders = ",".join("?" for _ in main_producers)
        rows = conn.execute(
            f"SELECT id, name, state_uf, lat, lon FROM flv_municipalities WHERE state_uf IN ({placeholders})",
            main_producers,
        ).fetchall()
        if rows:
            return [dict(r) for r in rows]

    rows = conn.execute("SELECT id, name, state_uf, lat, lon FROM flv_municipalities").fetchall()
    return [dict(r) for r in rows]


def _build_geo_legal_context(conn, culture, terminal=None, mun_id=None):
    """
    Build geoprocessed RJ/CNJ-216 context for the production cluster.

    CNJ 216/2026 is represented as a legal-status geocross: RJ/falencia records are
    weighted by status and distance to the production cluster/comarca proxy.
    """
    muns = _fetch_target_municipalities(conn, culture, terminal=terminal, mun_id=mun_id)
    points = [
        (int(m['id']), _safe_float(m.get('lat')), _safe_float(m.get('lon')))
        for m in muns if m.get('lat') is not None and m.get('lon') is not None
    ]
    if points:
        cluster_lat = sum(p[1] for p in points) / len(points)
        cluster_lon = sum(p[2] for p in points) / len(points)
    else:
        cluster_lat, cluster_lon = -15.0, -47.0

    try:
        rj_rows = conn.execute(
            """
            SELECT city, state_uf, lat, lon, judicial_status
            FROM flv_producers_rj
            WHERE status='ativo' AND lat IS NOT NULL AND lon IS NOT NULL
            """
        ).fetchall()
    except Exception:
        rj_rows = []

    weighted = 0.0
    severe_count = 0
    nearest = None
    centroid_weight = 0.0
    rj_lat_acc = 0.0
    rj_lon_acc = 0.0
    for row in rj_rows:
        lat = _safe_float(row['lat'])
        lon = _safe_float(row['lon'])
        status_weight = RJ_STATUS_WEIGHTS.get((row['judicial_status'] or '').strip(), 0.35)
        if points:
            distance = min(_haversine_km(lat, lon, p[1], p[2]) for p in points)
        else:
            distance = _haversine_km(lat, lon, cluster_lat, cluster_lon)
        geo_weight = math.exp(-distance / 120.0) if distance <= 350 else 0.0
        contribution = status_weight * geo_weight
        weighted += contribution
        if status_weight >= 0.85 and distance <= 180:
            severe_count += 1
        if nearest is None or distance < nearest:
            nearest = distance
        if contribution > 0:
            rj_lat_acc += lat * contribution
            rj_lon_acc += lon * contribution
            centroid_weight += contribution

    if centroid_weight > 0:
        rj_centroid_lat = rj_lat_acc / centroid_weight
        rj_centroid_lon = rj_lon_acc / centroid_weight
    else:
        rj_centroid_lat = cluster_lat
        rj_centroid_lon = cluster_lon

    rj_exposure_index = _clamp(weighted / 3.0)
    return {
        'mun_ids': [p[0] for p in points],
        'production_cluster_lat': cluster_lat,
        'production_cluster_lon': cluster_lon,
        'rj_centroid_lat': rj_centroid_lat,
        'rj_centroid_lon': rj_centroid_lon,
        'rj_nearest_km': nearest if nearest is not None else 999.0,
        'rj_geo_count_weighted': weighted,
        'rj_severe_count': severe_count,
        'rj_exposure_index': rj_exposure_index,
        'cnj216_geo_legal_index': rj_exposure_index,
    }


def _append_mun_filter(sql, mun_ids):
    if not mun_ids:
        return sql, []
    placeholders = ",".join("?" for _ in mun_ids)
    return sql.replace("WHERE obs_date >= ?", f"WHERE obs_date >= ? AND mun_id IN ({placeholders})"), list(mun_ids)


def _ndvi_stress(ndvi, ndvi_anomaly=None):
    base = _clamp((0.45 - _safe_float(ndvi, 0.55)) / 0.20)
    if ndvi_anomaly is not None:
        base = _clamp(base + max(0.0, -_safe_float(ndvi_anomaly)) * 1.5)
    return base

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
    """Build Prophet-compatible DataFrame dict with climate, legal and geo-vulnerability regressors."""
    from flv.db import get_conn
    from flv.model.thresholds import BR_HOLIDAYS_2026
    conn = get_conn()

    culture_row = conn.execute("SELECT id, main_producers FROM flv_cultures WHERE slug=?", (culture_slug,)).fetchone()
    if not culture_row:
        return []
    culture = dict(culture_row)
    geo_ctx = _build_geo_legal_context(conn, culture, terminal=terminal, mun_id=mun_id)

    # Get price series
    price_sql = "SELECT price_date as ds, price_avg as y FROM flv_ceasa_prices WHERE culture_id=?"
    params = [culture['id']]
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
    climate_sql, climate_filter_params = _append_mun_filter(climate_sql, geo_ctx['mun_ids'])
    climate_rows = conn.execute(climate_sql, (min_date, *climate_filter_params)).fetchall()
    climate_map = {r['obs_date']: dict(r) for r in climate_rows}

    # Get NDVI data
    ndvi_sql = "SELECT obs_date, AVG(ndvi_value) as ndvi, AVG(ndvi_anomaly) as ndvi_anomaly FROM flv_ndvi WHERE obs_date >= ? GROUP BY obs_date ORDER BY obs_date"
    ndvi_sql, ndvi_filter_params = _append_mun_filter(ndvi_sql, geo_ctx['mun_ids'])
    ndvi_rows = conn.execute(ndvi_sql, (min_date, *ndvi_filter_params)).fetchall()
    ndvi_map = {r['obs_date']: dict(r) for r in ndvi_rows}

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
    last_ndvi_anomaly = 0.0

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
        ndvi_row = ndvi_map.get(ds) or {}
        ndvi = ndvi_row.get('ndvi', last_ndvi)
        ndvi_anomaly = ndvi_row.get('ndvi_anomaly')
        if ndvi:
            last_ndvi = ndvi
        if ndvi_anomaly is not None:
            last_ndvi_anomaly = ndvi_anomaly

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
        ndvi_hydric_stress = _ndvi_stress(ndvi or last_ndvi, ndvi_anomaly if ndvi_anomaly is not None else last_ndvi_anomaly)
        precip_deficit = _clamp((12.0 - precip_7d) / 12.0)
        heat_stress = _clamp((temp_max - 32.0) / 8.0)
        open_meteo_stress = _clamp(0.55 * precip_deficit + 0.45 * heat_stress)
        legal_index = geo_ctx['cnj216_geo_legal_index']
        ndvi_legal_stress = _clamp(ndvi_hydric_stress * legal_index)
        open_meteo_legal_stress = _clamp(open_meteo_stress * legal_index)
        geo_vulnerability_index = _clamp(0.65 * ndvi_legal_stress + 0.35 * open_meteo_legal_stress)
        delta_judicial_pressure = geo_vulnerability_index
        if ndvi_hydric_stress >= 0.70 and legal_index >= 0.60:
            delta_judicial_pressure = max(delta_judicial_pressure, 0.90)

        result.append({
            'ds': ds,
            'y': y,
            'precip_7d': precip_7d,
            'temp_max_avg': temp_max,
            'ndvi': ndvi or last_ndvi,
            'ndvi_hydric_stress': ndvi_hydric_stress,
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
            'rj_exposure_index': legal_index,
            'cnj216_geo_legal_index': legal_index,
            'ndvi_legal_stress': ndvi_legal_stress,
            'open_meteo_legal_stress': open_meteo_legal_stress,
            'geo_vulnerability_index': geo_vulnerability_index,
            'delta_judicial_pressure': delta_judicial_pressure,
            'rj_nearest_km': geo_ctx['rj_nearest_km'],
            'rj_geo_count_weighted': geo_ctx['rj_geo_count_weighted'],
            'production_cluster_lat': geo_ctx['production_cluster_lat'],
            'production_cluster_lon': geo_ctx['production_cluster_lon'],
            'rj_centroid_lat': geo_ctx['rj_centroid_lat'],
            'rj_centroid_lon': geo_ctx['rj_centroid_lon'],
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
            'ndvi_hydric_stress': last.get('ndvi_hydric_stress', 0.0),
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
            'rj_exposure_index': last.get('rj_exposure_index', 0.0),
            'cnj216_geo_legal_index': last.get('cnj216_geo_legal_index', 0.0),
            'ndvi_legal_stress': last.get('ndvi_legal_stress', 0.0),
            'open_meteo_legal_stress': last.get('open_meteo_legal_stress', 0.0),
            'geo_vulnerability_index': last.get('geo_vulnerability_index', 0.0),
            'delta_judicial_pressure': last.get('delta_judicial_pressure', 0.0),
            'rj_nearest_km': last.get('rj_nearest_km', 999.0),
            'rj_geo_count_weighted': last.get('rj_geo_count_weighted', 0.0),
            'production_cluster_lat': last.get('production_cluster_lat', -15.0),
            'production_cluster_lon': last.get('production_cluster_lon', -47.0),
            'rj_centroid_lat': last.get('rj_centroid_lat', -15.0),
            'rj_centroid_lon': last.get('rj_centroid_lon', -47.0),
        })

    return future
