"""
GeoBrain API — Detecção de anomalias climáticas em polos agrícolas da América do Sul.
Endpoint: GET /api/geobrain/anomaly?region=all | ?lat=-12.5&lon=-55.7
"""
import json, os, time, threading, math
from datetime import datetime, timezone
import urllib.request

# ── Polos monitorados ────────────────────────────────────────────────────────
MONITORED_POLES = [
    {"name":"Mato Grosso",       "lat":-12.5,"lon":-55.7,"culture":"soja/milho",         "area_mha":9.2, "state":"MT"},
    {"name":"Paraná Norte",      "lat":-23.2,"lon":-51.2,"culture":"soja/trigo",          "area_mha":5.8, "state":"PR"},
    {"name":"MATOPIBA",          "lat": -7.5,"lon":-46.2,"culture":"soja",                "area_mha":4.1, "state":"TO/MA/PI/BA"},
    {"name":"Vale São Francisco","lat": -9.4,"lon":-40.5,"culture":"tomate/manga/uva",    "area_mha":0.4, "state":"PE/BA"},
    {"name":"Triângulo Mineiro", "lat":-18.9,"lon":-48.3,"culture":"tomate/batata",       "area_mha":0.3, "state":"MG"},
    {"name":"Cerrado Goiano",    "lat":-16.3,"lon":-49.3,"culture":"soja/milho",          "area_mha":3.2, "state":"GO"},
    {"name":"Sul RS",            "lat":-29.2,"lon":-51.2,"culture":"arroz/maça/uva",      "area_mha":2.1, "state":"RS"},
    {"name":"Pampa Argentino",   "lat":-33.5,"lon":-60.5,"culture":"soja/trigo",          "area_mha":15.0,"state":"ARG"},
    {"name":"Pampas Uruguai",    "lat":-33.0,"lon":-56.0,"culture":"soja/arroz",          "area_mha":1.8, "state":"URY"},
    {"name":"Santa Cruz Bolivia","lat":-17.8,"lon":-63.2,"culture":"soja",                "area_mha":1.4, "state":"BOL"},
]

# ── Cache in-memory (2 horas) ─────────────────────────────────────────────────
_CACHE = {}        # key: pole name → {"data": dict, "ts": float}
_CACHE_TTL = 7200  # segundos


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch_weather(lat, lon):
    """Busca previsão 7 dias na Open-Meteo. Retorna daily dict."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,et0_fao_evapotranspiration"
        "&timezone=America%2FSao_Paulo&forecast_days=7"
    )
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    return data.get("daily", {})


def _classify_status(score):
    if score <= 30:
        return "normal"
    if score <= 60:
        return "atenção"
    if score <= 80:
        return "alerta"
    return "crítico"


def _anomaly_types(tmax, tmin, precip7, et0_total, precip_total):
    types = []
    if tmax > 38:
        types.append("calor_extremo")
    if tmin < 4:
        types.append("geada")
    if precip_total < 5 and tmax > 32:
        types.append("seca_calor")
    if precip_total > 120:
        types.append("enchente")
    if et0_total > precip_total * 1.5:
        types.append("stress_hidrico")
    return types or None


def _build_recommendation(types, culture):
    if not types:
        return "Condições normais. Monitoramento padrão recomendado."
    recs = []
    if "calor_extremo" in types:
        recs.append(f"Irrigação emergencial para {culture} — temperaturas acima de 38°C prejudicam floração.")
    if "geada" in types:
        recs.append(f"Risco de geada para {culture} — acionar sistemas de proteção e seguro agrícola.")
    if "seca_calor" in types:
        recs.append(f"Déficit hídrico crítico para {culture} — priorize irrigação e adie adubações.")
    if "enchente" in types:
        recs.append(f"Excesso hídrico para {culture} — verifique drenagem e adie colheita se possível.")
    if "stress_hidrico" in types:
        recs.append(f"ET0 elevada para {culture} — monitore umidade do solo e ajuste irrigação.")
    return " | ".join(recs)


def _score_pole(pole):
    """Calcula anomalia para um polo. Retorna dict completo."""
    cached = _CACHE.get(pole["name"])
    if cached and (time.time() - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    daily = _fetch_weather(pole["lat"], pole["lon"])

    tmax_list  = daily.get("temperature_2m_max", [])
    tmin_list  = daily.get("temperature_2m_min", [])
    precip_list = daily.get("precipitation_sum", [])
    et0_list   = daily.get("et0_fao_evapotranspiration", [])

    def _safe(lst):
        return [v for v in lst if v is not None]

    tmax_max   = max(_safe(tmax_list))  if tmax_list  else 25.0
    tmin_min   = min(_safe(tmin_list))  if tmin_list  else 15.0
    precip_sum = sum(_safe(precip_list)) if precip_list else 0.0
    et0_sum    = sum(_safe(et0_list))   if et0_list   else 0.0

    score = 0
    if tmax_max > 38:
        score += 30
    if tmin_min < 4:
        score += 35
    if precip_sum < 5 and tmax_max > 32:
        score += 40
    if precip_sum > 120:
        score += 25
    if et0_sum > precip_sum * 1.5:
        score += 15

    score = min(score, 100)
    types = _anomaly_types(tmax_max, tmin_min, precip_sum, et0_sum, precip_sum)

    result = {
        "name":           pole["name"],
        "lat":            pole["lat"],
        "lon":            pole["lon"],
        "culture":        pole["culture"],
        "area_mha":       pole["area_mha"],
        "state":          pole["state"],
        "anomaly_score":  score,
        "status":         _classify_status(score),
        "anomaly_type":   ", ".join(types) if types else None,
        "tmax_7d":        round(tmax_max, 1),
        "tmin_7d":        round(tmin_min, 1),
        "precip_7d":      round(precip_sum, 1),
        "et0_7d":         round(et0_sum, 1),
        "recommendation": _build_recommendation(types, pole["culture"]),
        "last_updated":   _now_iso(),
    }

    _CACHE[pole["name"]] = {"data": result, "ts": time.time()}
    return result


def _process_all_poles(target_poles):
    results = [None] * len(target_poles)
    errors  = {}

    def worker(i, pole):
        try:
            results[i] = _score_pole(pole)
        except Exception as e:
            errors[pole["name"]] = str(e)
            results[i] = {
                "name":          pole["name"],
                "lat":           pole["lat"],
                "lon":           pole["lon"],
                "culture":       pole["culture"],
                "area_mha":      pole["area_mha"],
                "state":         pole["state"],
                "anomaly_score": 0,
                "status":        "indisponível",
                "anomaly_type":  None,
                "tmax_7d":       None,
                "tmin_7d":       None,
                "precip_7d":     None,
                "et0_7d":        None,
                "recommendation":"Dados indisponíveis temporariamente.",
                "last_updated":  _now_iso(),
                "error":         str(e),
            }

    threads = []
    for i, pole in enumerate(target_poles):
        t = threading.Thread(target=worker, args=(i, pole), daemon=True)
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=12)

    return results


def handle_geobrain_anomaly(handler, path):
    """Handler principal para /api/geobrain/anomaly"""
    try:
        # Parse query string
        qs = ""
        if "?" in path:
            qs = path.split("?", 1)[1]

        params = {}
        for part in qs.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.strip()] = v.strip()

        region = params.get("region", "all")
        lat_str = params.get("lat")
        lon_str = params.get("lon")

        # Seleciona polos
        if lat_str and lon_str:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                raise ValueError("lat/lon inválidos")
            # Polo mais próximo
            best = min(MONITORED_POLES, key=lambda p: math.hypot(p["lat"]-lat, p["lon"]-lon))
            target_poles = [best]
        else:
            target_poles = MONITORED_POLES

        poles_data = _process_all_poles(target_poles)

        critical_count = sum(1 for p in poles_data if p.get("status") == "crítico")
        alert_count    = sum(1 for p in poles_data if p.get("status") == "alerta")
        atencao_count  = sum(1 for p in poles_data if p.get("status") == "atenção")

        if critical_count > 0:
            summary = f"CRÍTICO: {critical_count} polo(s) em situação crítica requerem intervenção imediata."
        elif alert_count > 0:
            summary = f"ALERTA: {alert_count} polo(s) em alerta. Monitoramento intensivo recomendado."
        elif atencao_count > 0:
            summary = f"ATENÇÃO: {atencao_count} polo(s) em observação. Condições adversas detectadas."
        else:
            summary = "Condições normais em todos os polos monitorados."

        result = {
            "poles":          poles_data,
            "critical_count": critical_count,
            "alert_count":    alert_count,
            "atencao_count":  atencao_count,
            "total_poles":    len(poles_data),
            "summary":        summary,
            "generated_at":   _now_iso(),
        }

        data = json.dumps(result, ensure_ascii=False).encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(data)

    except Exception as e:
        err = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(err)
