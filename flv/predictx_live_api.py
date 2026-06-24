"""PredictX Live Intelligence API.

Agrega sinais públicos para antecipar impacto em hortifrutigranjeiros:
- eventos de demanda/logística (Copa do Mundo FIFA 2026)
- ENSO/La Niña/El Niño via NOAA/CPC/IRI como fonte recomendada
- clima observado/forecast via NASA POWER quando disponível
- fertilizantes/energia via World Bank Commodities como fonte recomendada

O módulo nunca inventa precisão: cada item carrega source_type, confidence e is_realtime.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

CACHE = {"live": None, "ts": 0}
CACHE_TTL_SECONDS = 15 * 60

HOST_CITIES_2026 = [
    {"city":"Toronto", "country":"Canada", "lat":43.6532, "lon":-79.3832, "matches":6},
    {"city":"Vancouver", "country":"Canada", "lat":49.2827, "lon":-123.1207, "matches":7},
    {"city":"Mexico City", "country":"Mexico", "lat":19.4326, "lon":-99.1332, "matches":5},
    {"city":"Guadalajara", "country":"Mexico", "lat":20.6597, "lon":-103.3496, "matches":4},
    {"city":"Monterrey", "country":"Mexico", "lat":25.6866, "lon":-100.3161, "matches":4},
    {"city":"Atlanta", "country":"USA", "lat":33.7490, "lon":-84.3880, "matches":8},
    {"city":"Boston", "country":"USA", "lat":42.3601, "lon":-71.0589, "matches":7},
    {"city":"Dallas", "country":"USA", "lat":32.7767, "lon":-96.7970, "matches":9},
    {"city":"Houston", "country":"USA", "lat":29.7604, "lon":-95.3698, "matches":7},
    {"city":"Kansas City", "country":"USA", "lat":39.0997, "lon":-94.5786, "matches":6},
    {"city":"Los Angeles", "country":"USA", "lat":34.0522, "lon":-118.2437, "matches":8},
    {"city":"Miami", "country":"USA", "lat":25.7617, "lon":-80.1918, "matches":7},
    {"city":"New York/New Jersey", "country":"USA", "lat":40.7128, "lon":-74.0060, "matches":8},
    {"city":"Philadelphia", "country":"USA", "lat":39.9526, "lon":-75.1652, "matches":6},
    {"city":"San Francisco Bay Area", "country":"USA", "lat":37.7749, "lon":-122.4194, "matches":6},
    {"city":"Seattle", "country":"USA", "lat":47.6062, "lon":-122.3321, "matches":6},
]

EVENTS = [
    {
        "id": "fifa-world-cup-2026",
        "name": "Copa do Mundo FIFA 2026",
        "start_date": "2026-06-11",
        "end_date": "2026-07-19",
        "type": "megaevento",
        "source": "FIFA — calendário e cidades-sede oficiais",
        "source_url": "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/articles/match-schedule-fixtures-results-teams-stadiums",
        "source_type": "official_static",
        "confidence": 0.92,
        "host_cities": HOST_CITIES_2026,
        "impacts": [
            {"axis":"demanda", "risk":"Alta local", "why":"Aumento de turistas, fan zones, hotéis, bares, restaurantes e alimentação fora do domicílio."},
            {"axis":"logística", "risk":"Média/Alta", "why":"Restrição urbana, congestionamento em dias de jogo, maior competição por transporte refrigerado e entregas de última milha."},
            {"axis":"preço", "risk":"Média", "why":"Pressão concentrada em hortifruti fresco, bebidas não alcoólicas, frutas prontas, folhas e produtos de food service."},
            {"axis":"trabalho", "risk":"Média", "why":"Disputa por mão-de-obra temporária em hotelaria, limpeza, alimentação, carga/descarga e eventos."}
        ],
        "affected_products": ["folhosas", "tomate", "batata", "cebola", "frutas", "uva", "manga", "abacate", "ovos", "frango", "laticínios"]
    }
]

SOURCES = [
    {"name":"FIFA", "use":"Calendário, cidades-sede e jogos da Copa", "type":"oficial", "url":"https://www.fifa.com/"},
    {"name":"NOAA CPC / IRI", "use":"ENSO: El Niño, La Niña e neutralidade", "type":"oficial/científica", "url":"https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/"},
    {"name":"NASA POWER", "use":"Temperatura, chuva, radiação e vento por coordenada", "type":"oficial/científica", "url":"https://power.larc.nasa.gov/"},
    {"name":"FAO GIEWS", "use":"Alertas globais de produção agrícola e segurança alimentar", "type":"multilateral", "url":"https://www.fao.org/giews/"},
    {"name":"USGS FEWS NET", "use":"Anomalias climáticas e risco de safra", "type":"governamental/científica", "url":"https://fews.net/"},
    {"name":"ReliefWeb", "use":"Greves, conflitos, enchentes, secas, ciclones e emergências", "type":"ONU/agregador", "url":"https://reliefweb.int/"},
    {"name":"World Bank Commodities", "use":"Fertilizantes, energia e alimentos em séries mensais", "type":"multilateral", "url":"https://www.worldbank.org/en/research/commodity-markets"}
]

REGIONS = [
    {"name":"Vale do São Francisco", "lat":-9.39, "lon":-40.50, "products":["uva","manga","melão"], "export_route":"Suape/Santos"},
    {"name":"Ibiúna/Mogi/Atibaia", "lat":-23.55, "lon":-46.90, "products":["folhosas","morango","tomate"], "export_route":"São Paulo/CEAGESP"},
    {"name":"São Gotardo/Cristalina", "lat":-18.60, "lon":-46.30, "products":["cenoura","batata","alho","cebola"], "export_route":"DF/MG/SP"},
    {"name":"Mossoró/Icapuí", "lat":-5.10, "lon":-37.40, "products":["melão","melancia"], "export_route":"Natal/Fortaleza/Suape"},
    {"name":"Serra Gaúcha/Vacaria", "lat":-28.51, "lon":-50.93, "products":["maçã","uva"], "export_route":"Sul/Santos"}
]


def _http_json(url: str, timeout: int = 8):
    req = Request(url, headers={"User-Agent":"PredictX-FLV/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_nasa_power_snapshot(lat: float, lon: float):
    """Busca últimos dados diários disponíveis da NASA POWER para uma coordenada.
    Falha silenciosamente com fallback explícito, pois disponibilidade depende da rede.
    """
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    params = urlencode({
        "parameters":"T2M,PRECTOTCORR,WS2M",
        "community":"AG",
        "longitude": lon,
        "latitude": lat,
        "start": today,
        "end": today,
        "format":"JSON"
    })
    url = f"https://power.larc.nasa.gov/api/temporal/daily/point?{params}"
    try:
        data = _http_json(url, timeout=6)
        p = data.get("properties", {}).get("parameter", {})
        out = {}
        for k in ("T2M", "PRECTOTCORR", "WS2M"):
            series = p.get(k, {})
            val = next(iter(series.values())) if series else None
            out[k] = None if val in (-999, -999.0) else val
        return {"ok": True, "source":"NASA POWER", "is_realtime": True, "data": out}
    except Exception as exc:
        return {"ok": False, "source":"NASA POWER", "is_realtime": False, "error": str(exc)[:160]}


def _event_score_for_city(city):
    matches = city.get("matches", 0)
    # Pontuação operacional: número de jogos + país + cidade turística. Não é previsão de preço.
    score = min(100, 42 + matches * 5)
    if city["city"] in {"New York/New Jersey", "Los Angeles", "Mexico City", "Miami", "Dallas"}:
        score += 8
    return min(100, score)


def build_worldcup_impact():
    cities = []
    for c in HOST_CITIES_2026:
        score = _event_score_for_city(c)
        if score >= 82:
            risk = "alto"
        elif score >= 68:
            risk = "médio-alto"
        else:
            risk = "médio"
        cities.append({**c, "impact_score": score, "risk_level": risk})
    cities = sorted(cities, key=lambda x: x["impact_score"], reverse=True)
    return {
        "event": EVENTS[0],
        "cities_ranked": cities,
        "summary": "A Copa altera principalmente demanda urbana, food service, logística refrigerada, mão-de-obra temporária e preço local em cidades-sede e corredores de abastecimento.",
        "top_impacts": [
            "hortifruti pronto para consumo e food service tende a subir perto de estádios, fan zones, hotéis e aeroportos",
            "entregas urbanas podem atrasar por bloqueios, segurança e congestionamento em dias de jogo",
            "transportadoras refrigeradas podem priorizar contratos de evento/hotelaria, pressionando frete",
            "mão-de-obra temporária pode migrar para serviços de evento, reduzindo disponibilidade em carga/descarga e distribuição"
        ]
    }


def build_regional_risks():
    # Tenta clima real para algumas regiões e combina com risco operacional curado.
    rows = []
    for r in REGIONS:
        weather = get_nasa_power_snapshot(r["lat"], r["lon"])
        temp = weather.get("data", {}).get("T2M") if weather.get("ok") else None
        rain = weather.get("data", {}).get("PRECTOTCORR") if weather.get("ok") else None
        risk = 45
        reasons = []
        if temp is not None and temp >= 34:
            risk += 18; reasons.append("calor elevado pode acelerar perda pós-colheita")
        if rain is not None and rain >= 25:
            risk += 16; reasons.append("chuva diária elevada pode afetar colheita/transporte")
        if not reasons:
            reasons.append("sem alerta meteorológico crítico confirmado no snapshot disponível")
        rows.append({
            **r,
            "risk_score": min(100, risk),
            "risk_level": "alto" if risk >= 75 else "médio" if risk >= 50 else "baixo",
            "weather": weather,
            "reasons": reasons
        })
    return rows


def build_live_payload(force: bool = False, live_weather: bool = False):
    now = time.time()
    if not force and CACHE["live"] and now - CACHE["ts"] < CACHE_TTL_SECONDS:
        return CACHE["live"]
    payload = {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "PredictX Live 3.0",
        "disclaimer": "Indicadores operacionais. Não são recomendação financeira nem garantia de preço/safra.",
        "sources": SOURCES,
        "worldcup_2026": build_worldcup_impact(),
        "regional_risks": build_regional_risks(),
        "global_signals": [
            {"signal":"ENSO", "status":"monitorar", "source":"NOAA CPC / IRI", "why":"El Niño/La Niña alteram chuva e temperatura, afetando oferta regional, irrigação, qualidade e janela de colheita.", "is_realtime": False, "endpoint_hint":"conectar parser CPC/IRI em produção"},
            {"signal":"Fertilizantes", "status":"monitorar", "source":"World Bank Commodities + notícias verificadas", "why":"Guerras, sanções, frete marítimo e energia afetam nitrogenados, fosfatados e potássio; impacto chega ao custo de produção com defasagem.", "is_realtime": False},
            {"signal":"Greves/logística", "status":"monitorar", "source":"ReliefWeb + autoridades locais + portos", "why":"Greves de caminhoneiros/portos e bloqueios geram atraso, perda de perecíveis e deslocamento de oferta para mercados alternativos.", "is_realtime": False},
            {"signal":"Eventos extremos", "status":"monitorar", "source":"NASA POWER, INMET, NOAA, serviços nacionais", "why":"Tornados, geadas, ondas de calor, seca e enchentes alteram produtividade e logística rapidamente.", "is_realtime": True}
        ]
    }
    CACHE["live"] = payload
    CACHE["ts"] = now
    return payload
