"""FLV Anticipation Factor — Climate Thresholds for Producer Regions."""
import time, json, urllib.request

ANTICIPATION_THRESHOLDS = {
    # ═══ SUDESTE — Cinturao Verde SP/MG (maior mercado consumidor) ═══
    "cinturao_verde_sp": {
        "ibge": "3548906", "lat": -23.55, "lon": -46.63,
        "cultures": ["folhosas", "tomate", "morango", "cenoura", "pimentao"],
        "rules": [
            {"type": "geada",         "metric": "temp_min_c", "op": "lt", "val": 5.0,
             "supply": -40, "price": 60, "severity": "vermelho",
             "msg": "Geada no Cinturao Verde SP — colapso imediato de folhosas e morango na CEAGESP"},
            {"type": "excesso_chuva", "metric": "precip_7d",  "op": "gt", "val": 100.0,
             "supply": -20, "price": 30, "severity": "laranja",
             "msg": "Chuva excessiva no Cinturao Verde — apodrecimento em campo, queda de oferta CEAGESP"},
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 5.0,
             "supply": -15, "price": 25, "severity": "laranja",
             "msg": "Deficit hidrico severo SP — irrigacao insuficiente para hortalicas"},
        ]
    },
    "triangulo_mineiro": {
        "ibge": "3170206", "lat": -19.00, "lon": -47.95,
        "cultures": ["tomate", "batata", "cebola", "cenoura", "alho"],
        "rules": [
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 3.0,
             "supply": -25, "price": 35, "severity": "laranja",
             "msg": "Seca no Triangulo Mineiro — batata e tomate irrigados sob estresse"},
            {"type": "geada",         "metric": "temp_min_c", "op": "lt", "val": 3.0,
             "supply": -30, "price": 45, "severity": "vermelho",
             "msg": "Geada no Triangulo Mineiro — perda de safra de batata e tomate"},
        ]
    },
    "cristalina_go": {
        "ibge": "5206206", "lat": -16.77, "lon": -47.62,
        "cultures": ["tomate", "batata", "cebola", "alho"],
        "rules": [
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 3.0,
             "supply": -20, "price": 30, "severity": "laranja",
             "msg": "Seca em Cristalina-GO — polo irrigado de hortalicas sob pressao hidrica"},
            {"type": "onda_calor",    "metric": "temp_max_c", "op": "gt", "val": 38.0,
             "supply": -15, "price": 20, "severity": "amarelo",
             "msg": "Calor extremo no Cerrado — estresse termico em culturas de inverno"},
        ]
    },

    # ═══ SUL — Maior polo de cebola, maca, pessego, uva ═══
    "serra_gaucha": {
        "ibge": "4302105", "lat": -29.17, "lon": -51.52,
        "cultures": ["uva", "maca", "pessego", "morango"],
        "rules": [
            {"type": "geada",         "metric": "temp_min_c", "op": "lt", "val": -2.0,
             "supply": -35, "price": 50, "severity": "vermelho",
             "msg": "Geada severa na Serra Gaucha — dano critico em videiras e pomares"},
            {"type": "granizo",       "metric": "precip_1h",  "op": "gt", "val": 25.0,
             "supply": -45, "price": 70, "severity": "vermelho",
             "msg": "Granizo na Serra Gaucha — destruicao mecanica de uva e maca"},
            {"type": "excesso_chuva", "metric": "precip_7d",  "op": "gt", "val": 150.0,
             "supply": -15, "price": 20, "severity": "amarelo",
             "msg": "Excesso de umidade — risco fitossanitario em videiras"},
        ]
    },
    "ituporanga_sc": {
        "ibge": "4208203", "lat": -27.41, "lon": -49.60,
        "cultures": ["cebola", "alho", "batata"],
        "rules": [
            {"type": "excesso_chuva", "metric": "precip_7d",  "op": "gt", "val": 120.0,
             "supply": -25, "price": 35, "severity": "laranja",
             "msg": "Chuva excessiva em Ituporanga-SC — capital nacional da cebola sob risco de perda"},
            {"type": "geada",         "metric": "temp_min_c", "op": "lt", "val": 0.0,
             "supply": -20, "price": 30, "severity": "laranja",
             "msg": "Geada em SC — impacto na safra de cebola e alho do Sul"},
        ]
    },

    # ═══ NORDESTE — Vale do Sao Francisco (maior polo irrigado) ═══
    "vale_sao_francisco": {
        "ibge": "2611101", "lat": -9.39, "lon": -40.50,
        "cultures": ["manga", "uva", "melao", "goiaba", "coco", "mamao"],
        "rules": [
            {"type": "onda_calor",    "metric": "temp_max_c", "op": "gt", "val": 40.0,
             "supply": -25, "price": 35, "severity": "laranja",
             "msg": "Onda de calor no VSF (Petrolina/Juazeiro) — estresse hidrico em fruticultura irrigada"},
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 1.0,
             "supply": -15, "price": 22, "severity": "amarelo",
             "msg": "Seca extrema no semiarido — pressao sobre reservatorios de irrigacao do VSF"},
        ]
    },
    "mossoro_rn": {
        "ibge": "2408003", "lat": -5.19, "lon": -37.34,
        "cultures": ["melao", "melancia", "mamao", "banana"],
        "rules": [
            {"type": "onda_calor",    "metric": "temp_max_c", "op": "gt", "val": 39.0,
             "supply": -15, "price": 20, "severity": "amarelo",
             "msg": "Calor intenso em Mossoro-RN — estresse em melao e melancia"},
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 1.0,
             "supply": -20, "price": 25, "severity": "laranja",
             "msg": "Seca no polo meloeiro RN/CE — queda de producao nos proximos 15 dias"},
        ]
    },
    "sul_bahia_es": {
        "ibge": "2933307", "lat": -17.54, "lon": -39.74,
        "cultures": ["mamao", "banana", "coco", "abacaxi"],
        "rules": [
            {"type": "excesso_chuva", "metric": "precip_7d",  "op": "gt", "val": 130.0,
             "supply": -20, "price": 25, "severity": "laranja",
             "msg": "Chuvas intensas no Sul da Bahia/ES — risco de sigatoka em banana e queda de mamao"},
            {"type": "onda_calor",    "metric": "temp_max_c", "op": "gt", "val": 38.0,
             "supply": -10, "price": 15, "severity": "amarelo",
             "msg": "Calor excessivo — maturacao acelerada de mamao, risco de excesso momentaneo"},
        ]
    },

    # ═══ CENTRO-OESTE — Cerrado irrigado ═══
    "matopiba": {
        "ibge": "2105302", "lat": -7.53, "lon": -46.04,
        "cultures": ["melancia", "banana", "abacaxi"],
        "rules": [
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 2.0,
             "supply": -15, "price": 20, "severity": "amarelo",
             "msg": "Seca na fronteira MATOPIBA — reducao de oferta de melancia e abacaxi"},
        ]
    },

    # ═══ NORTE — Acai e frutas tropicais ═══
    "para_acai": {
        "ibge": "1501402", "lat": -1.46, "lon": -48.50,
        "cultures": ["acai", "banana", "abacaxi", "maracuja"],
        "rules": [
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 10.0,
             "supply": -30, "price": 45, "severity": "laranja",
             "msg": "Seca atipica na Amazonia — producao de acai em risco, preco deve disparar"},
            {"type": "excesso_chuva", "metric": "precip_7d",  "op": "gt", "val": 200.0,
             "supply": -10, "price": 15, "severity": "amarelo",
             "msg": "Cheias no Para — logistica de escoamento de acai comprometida"},
        ]
    },

    # ═══ CITRUS BELT SP ═══
    "citrus_belt_sp": {
        "ibge": "3526902", "lat": -22.56, "lon": -47.40,
        "cultures": ["laranja", "limao", "tangerina"],
        "rules": [
            {"type": "seca",          "metric": "precip_7d",  "op": "lt", "val": 5.0,
             "supply": -20, "price": 30, "severity": "laranja",
             "msg": "Seca no Citrus Belt SP — queda de producao de laranja afeta suco e mesa"},
            {"type": "geada",         "metric": "temp_min_c", "op": "lt", "val": 2.0,
             "supply": -40, "price": 60, "severity": "vermelho",
             "msg": "Geada no cinturao citricola — perda massiva de laranja, limao e tangerina"},
        ]
    },

    # ═══ VALE DO RIBEIRA SP — Banana ═══
    "vale_ribeira_sp": {
        "ibge": "3524600", "lat": -24.49, "lon": -47.84,
        "cultures": ["banana", "maracuja"],
        "rules": [
            {"type": "excesso_chuva", "metric": "precip_7d",  "op": "gt", "val": 150.0,
             "supply": -20, "price": 25, "severity": "laranja",
             "msg": "Chuvas intensas no Vale do Ribeira — risco de sigatoka e deslizamentos"},
            {"type": "geada",         "metric": "temp_min_c", "op": "lt", "val": 5.0,
             "supply": -15, "price": 20, "severity": "amarelo",
             "msg": "Frio no Vale do Ribeira — crescimento de banana desacelerado"},
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
