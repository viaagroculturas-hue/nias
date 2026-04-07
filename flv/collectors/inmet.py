"""FLV INMET Climate Collector — Weather stations + Open-Meteo fallback."""
import urllib.request, json, time
from datetime import datetime, timedelta

def fetch_all():
    """Fetch climate data for all FLV producer municipalities."""
    from flv.db import get_conn
    conn = get_conn()
    muns = conn.execute("SELECT id, ibge_code, name, lat, lon, inmet_station FROM flv_municipalities").fetchall()
    inserted = 0

    for mun in muns:
        try:
            count = _fetch_openmeteo(conn, mun)
            inserted += count
        except Exception as e:
            print(f'[FLV-INMET] Erro {mun["name"]}: {e}')

    conn.commit()
    print(f'[FLV-INMET] {inserted} observacoes climaticas inseridas')
    return inserted

def _fetch_openmeteo(conn, mun):
    """Fetch 7-day historical + current from Open-Meteo."""
    url = (f"https://api.open-meteo.com/v1/forecast?"
           f"latitude={mun['lat']}&longitude={mun['lon']}"
           f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean,wind_speed_10m_max"
           f"&timezone=America/Sao_Paulo&past_days=7&forecast_days=1")
    req = urllib.request.Request(url, headers={'User-Agent': 'NIA$-FLV/1.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())

    daily = data.get('daily', {})
    dates = daily.get('time', [])
    count = 0

    for i, date in enumerate(dates):
        temp_max = (daily.get('temperature_2m_max') or [None]*len(dates))[i]
        temp_min = (daily.get('temperature_2m_min') or [None]*len(dates))[i]
        precip = (daily.get('precipitation_sum') or [None]*len(dates))[i]
        humidity = (daily.get('relative_humidity_2m_mean') or [None]*len(dates))[i]
        wind = (daily.get('wind_speed_10m_max') or [None]*len(dates))[i]

        try:
            conn.execute(
                "INSERT OR REPLACE INTO flv_climate (mun_id,obs_date,temp_max_c,temp_min_c,precip_mm,humidity_pct,wind_ms,source) VALUES (?,?,?,?,?,?,?,?)",
                (mun['id'], date, temp_max, temp_min, precip, humidity, wind, 'Open-Meteo')
            )
            count += 1
        except Exception:
            pass

    return count

def _fetch_inmet_station(station_code, days=7):
    """Fetch from INMET API — fallback if Open-Meteo fails."""
    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        url = f"https://apitempo.inmet.gov.br/estacao/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}/{station_code}"
        req = urllib.request.Request(url, headers={'User-Agent': 'NIA$-FLV/1.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception:
        return []
