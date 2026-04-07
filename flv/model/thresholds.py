"""FLV Anticipation Factor — Climate Thresholds for Producer Regions."""
import time, json, urllib.request

ANTICIPATION_THRESHOLDS = {
    "gravata_pe": {
        "ibge": "2606101", "lat": -8.2044, "lon": -35.5620,
        "cultures": ["tomate", "pimentao", "folhosas", "cenoura"],
        "rules": [
            {"type": "geada",         "metric": "temp_min_c", "op": "lt", "val": 8.0,
             "supply": -25, "price": 40, "severity": "vermelho",
             "msg": "Temperatura minima critica para horticultura de altitude em Gravata-PE"},
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 5.0,
             "supply": -15, "price": 20, "severity": "laranja",
             "msg": "Deficit hidrico severo no Agreste pernambucano"},
            {"type": "excesso_chuva", "metric": "precip_7d",  "op": "gt", "val": 120.0,
             "supply": -10, "price": 15, "severity": "amarelo",
             "msg": "Excesso de precipitacao — risco de apodrecimento e erosao"},
        ]
    },
    "petrolina_pe": {
        "ibge": "2611101", "lat": -9.3891, "lon": -40.5028,
        "cultures": ["uva", "manga", "tomate", "melao"],
        "rules": [
            {"type": "onda_calor", "metric": "temp_max_c", "op": "gt", "val": 40.0,
             "supply": -20, "price": 30, "severity": "laranja",
             "msg": "Onda de calor no Vale do Sao Francisco — estresse em fruticultura irrigada"},
            {"type": "seca",       "metric": "precip_7d",  "op": "lt", "val": 2.0,
             "supply": -10, "price": 18, "severity": "amarelo",
             "msg": "Precipitacao minima em area irrigada — pressao sobre recursos hidricos"},
        ]
    },
    "holambra_sp": {
        "ibge": "3519055", "lat": -22.6347, "lon": -47.0597,
        "cultures": ["folhosas", "morango", "pimentao"],
        "rules": [
            {"type": "geada",   "metric": "temp_min_c", "op": "lt", "val": 4.0,
             "supply": -35, "price": 55, "severity": "vermelho",
             "msg": "Geada em Holambra — risco critico para folhosas e morango"},
            {"type": "granizo", "metric": "precip_1h",  "op": "gt", "val": 30.0,
             "supply": -50, "price": 80, "severity": "vermelho",
             "msg": "Risco de granizo — dano mecanico severo em culturas sensiveis"},
        ]
    },
}

# Brazilian market holidays that affect CEASA volumes
BR_HOLIDAYS_2026 = [
    ("2026-01-01", "Confraternizacao"),
    ("2026-02-16", "Carnaval"), ("2026-02-17", "Carnaval"),
    ("2026-04-03", "Sexta-feira Santa"),
    ("2026-04-21", "Tiradentes"),
    ("2026-05-01", "Trabalho"),
    ("2026-06-04", "Corpus Christi"),
    ("2026-06-24", "Sao Joao"),
    ("2026-09-07", "Independencia"),
    ("2026-10-12", "N.S.Aparecida"),
    ("2026-11-02", "Finados"),
    ("2026-11-15", "Proclamacao"),
    ("2026-12-25", "Natal"),
]

def _fetch_weather(lat, lon):
    """Fetch current weather from Open-Meteo for threshold evaluation."""
    try:
        url = (f"https://api.open-meteo.com/v1/forecast?"
               f"latitude={lat}&longitude={lon}"
               f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
               f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum"
               f"&timezone=America/Sao_Paulo&forecast_days=7")
        req = urllib.request.Request(url, headers={'User-Agent': 'NIA$-FLV/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        print(f'[FLV-Threshold] Weather fetch error: {e}')
        return None

def evaluate_realtime():
    """Evaluate all thresholds against current weather. Insert alerts into DB."""
    from flv.db import get_conn
    conn = get_conn()
    alerts_generated = 0

    for region_key, cfg in ANTICIPATION_THRESHOLDS.items():
        weather = _fetch_weather(cfg['lat'], cfg['lon'])
        if not weather:
            continue

        daily = weather.get('daily', {})
        current = weather.get('current', {})

        # Build metrics
        precip_7d = sum(daily.get('precipitation_sum', []) or [0])
        temp_max_vals = daily.get('temperature_2m_max', [])
        temp_min_vals = daily.get('temperature_2m_min', [])
        metrics = {
            'temp_max_c': max(temp_max_vals) if temp_max_vals else None,
            'temp_min_c': min(temp_min_vals) if temp_min_vals else None,
            'precip_7d': precip_7d,
            'precip_1h': current.get('precipitation', 0),
        }

        for rule in cfg['rules']:
            metric_val = metrics.get(rule['metric'])
            if metric_val is None:
                continue

            triggered = False
            if rule['op'] == 'lt' and metric_val < rule['val']:
                triggered = True
            elif rule['op'] == 'gt' and metric_val > rule['val']:
                triggered = True

            if triggered:
                # Check if similar alert already exists in last 6h
                existing = conn.execute(
                    "SELECT id FROM flv_alerts WHERE region_key=? AND alert_type=? AND created_at > datetime('now','-6 hours')",
                    (region_key, rule['type'])
                ).fetchone()
                if existing:
                    continue

                # Get culture IDs
                for cult_slug in cfg['cultures']:
                    cid = conn.execute("SELECT id FROM flv_cultures WHERE slug=?", (cult_slug,)).fetchone()
                    mid = conn.execute("SELECT id FROM flv_municipalities WHERE ibge_code=?", (cfg['ibge'],)).fetchone()
                    if not cid:
                        continue
                    conn.execute(
                        "INSERT INTO flv_alerts (culture_id,mun_id,region_key,alert_type,severity,trigger_value,threshold_value,impact_supply_pct,impact_price_pct,message,valid_until) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,datetime('now','+48 hours'))",
                        (cid['id'], mid['id'] if mid else None, region_key, rule['type'],
                         rule['severity'], metric_val, rule['val'],
                         rule['supply'], rule['price'], rule['msg'])
                    )
                    alerts_generated += 1

        conn.commit()

    if alerts_generated:
        print(f'[FLV-Threshold] {alerts_generated} alertas gerados')
    return alerts_generated

def is_holiday(date_str):
    """Check if date_str (YYYY-MM-DD) is a Brazilian market holiday."""
    return any(h[0] == date_str for h in BR_HOLIDAYS_2026)
