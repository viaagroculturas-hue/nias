"""API de inteligência de risco agroclimático/logístico.

Objetivo: combinar fontes oficiais/seguras com regras transparentes para antecipar
risco de quebra de safra por clima, mão de obra/logística, ENSO, fertilizantes,
guerras, greves e eventos extremos.

A API não inventa coleta: quando uma fonte externa não responde, retorna o status
`fallback_curated` e marca a confiança menor.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_PATH = os.path.join(os.path.dirname(__file__), "safe_sources_risk.json")

DEFAULT_POLES = [
    {"id": "br_sp_cinturao", "name": "Cinturão Verde SP", "country": "Brasil", "lat": -23.55, "lon": -46.63, "products": ["folhosas", "tomate", "pimentão"]},
    {"id": "br_mg_ceasa", "name": "Sul de Minas / Triângulo", "country": "Brasil", "lat": -21.24, "lon": -45.00, "products": ["batata", "café", "hortaliças"]},
    {"id": "br_ba_juazeiro", "name": "Juazeiro-Petrolina", "country": "Brasil", "lat": -9.41, "lon": -40.50, "products": ["uva", "manga", "melão"]},
    {"id": "br_rs_serra", "name": "Serra Gaúcha / Vacaria", "country": "Brasil", "lat": -28.50, "lon": -50.94, "products": ["maçã", "uva", "hortaliças"]},
    {"id": "cl_coquimbo", "name": "Coquimbo-Valparaíso", "country": "Chile", "lat": -30.0, "lon": -71.3, "products": ["uva", "palta", "cítricos"]},
    {"id": "pe_ica", "name": "Ica / La Libertad", "country": "Peru", "lat": -14.07, "lon": -75.73, "products": ["uva", "aspargos", "arándano"]},
    {"id": "ar_mendoza", "name": "Mendoza / San Juan", "country": "Argentina", "lat": -32.89, "lon": -68.84, "products": ["uva", "alho", "frutas"]},
    {"id": "co_antioquia", "name": "Antioquia / Cundinamarca", "country": "Colômbia", "lat": 6.25, "lon": -75.56, "products": ["batata", "hortaliças", "frutas"]}
]

FALLBACK_ENSO = {
    "phase": "monitorar",
    "probability": None,
    "message": "ENSO deve ser validado em NOAA CPC e IRI/CPC; sem coleta online no ciclo atual.",
    "source_status": "fallback_curated"
}


def _load_sources() -> Dict[str, Any]:
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _http_get_json(url: str, timeout: int = 12) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "NIA-risk-intelligence/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    return json.loads(raw)


def _http_get_text(url: str, timeout: int = 12) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "NIA-risk-intelligence/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _score(value: float, low: float, high: float) -> int:
    if value <= low:
        return 0
    if value >= high:
        return 100
    return int(round((value - low) * 100 / (high - low)))


def _severity(score: int) -> str:
    if score >= 75:
        return "crítico"
    if score >= 55:
        return "alto"
    if score >= 35:
        return "atenção"
    return "baixo"


def fetch_enso_signal() -> Dict[str, Any]:
    url = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml"
    try:
        text = _http_get_text(url, timeout=10)
        plain = re.sub(r"<[^>]+>", " ", text)
        plain = re.sub(r"\s+", " ", plain)
        window = plain[:3000]
        phase = "neutro"
        if re.search(r"El Ni[nñ]o", window, re.I):
            phase = "El Niño"
        if re.search(r"La Ni[nñ]a", window, re.I):
            # se ambos aparecem, mantém o último sinal textual apenas como monitoramento
            phase = "La Niña" if "La Niña" in window[:800] else phase
        probs = [int(x) for x in re.findall(r"(\d{2,3})\s*%", window)]
        probability = max([p for p in probs if 0 <= p <= 100], default=None)
        return {
            "phase": phase,
            "probability": probability,
            "message": window[:420].strip(),
            "source": "NOAA CPC ENSO Diagnostic Discussion",
            "source_url": url,
            "source_status": "online_observed",
        }
    except Exception as exc:
        data = dict(FALLBACK_ENSO)
        data["error"] = str(exc)
        return data


def fetch_nasa_power_point(lat: float, lon: float, days: int = 30) -> Dict[str, Any]:
    end = datetime.now(timezone.utc).date() - timedelta(days=2)
    start = end - timedelta(days=max(days - 1, 1))
    params = {
        "parameters": "T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M,WS2M",
        "community": "AG",
        "longitude": str(lon),
        "latitude": str(lat),
        "start": start.strftime("%Y%m%d"),
        "end": end.strftime("%Y%m%d"),
        "format": "JSON",
    }
    url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urllib.parse.urlencode(params)
    data = _http_get_json(url, timeout=14)
    params_data = data.get("properties", {}).get("parameter", {})
    prec = list((params_data.get("PRECTOTCORR") or {}).values())
    tmax = list((params_data.get("T2M_MAX") or {}).values())
    wind = list((params_data.get("WS2M") or {}).values())
    total_rain = round(sum(float(x) for x in prec if x is not None), 1) if prec else None
    avg_tmax = round(sum(float(x) for x in tmax if x is not None) / len(tmax), 1) if tmax else None
    max_wind = round(max(float(x) for x in wind if x is not None), 1) if wind else None
    drought_score = 0 if total_rain is None else _score(35 - total_rain, 0, 35)
    heat_score = 0 if avg_tmax is None else _score(avg_tmax, 29, 38)
    wind_score = 0 if max_wind is None else _score(max_wind, 7, 18)
    climate_score = max(drought_score, heat_score, wind_score)
    return {
        "source_status": "online_observed",
        "source": "NASA POWER Daily API",
        "period": {"start": start.isoformat(), "end": end.isoformat(), "days": days},
        "metrics": {"rain_mm": total_rain, "avg_tmax_c": avg_tmax, "max_wind_ms": max_wind},
        "scores": {"seca": drought_score, "calor": heat_score, "vento": wind_score, "clima": climate_score},
        "severity": _severity(climate_score),
        "url": url,
    }


def fetch_reliefweb_events(query: str = "fertilizer OR strike OR drought OR flood OR storm OR conflict", days: int = 60) -> Dict[str, Any]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "appname": "nia-risk-intelligence",
        "profile": "list",
        "limit": 10,
        "query[value]": query,
        "filter[field]": "date.created",
        "filter[value][from]": since,
        "sort[]": "date.created:desc",
        "fields[include][]": ["title", "date.created", "country.name", "source.name", "url"]
    }
    url = "https://api.reliefweb.int/v1/reports?" + urllib.parse.urlencode(payload, doseq=True)
    try:
        data = _http_get_json(url, timeout=12)
        events = []
        for item in data.get("data", []):
            f = item.get("fields", {})
            countries = f.get("country", []) or []
            sources = f.get("source", []) or []
            events.append({
                "title": f.get("title"),
                "date": (f.get("date", {}) or {}).get("created"),
                "countries": [c.get("name") for c in countries if c.get("name")],
                "sources": [s.get("name") for s in sources if s.get("name")],
                "url": f.get("url"),
            })
        return {"source_status": "online_observed", "source": "ReliefWeb API", "count": len(events), "events": events, "url": url}
    except Exception as exc:
        return {"source_status": "fallback_curated", "source": "ReliefWeb API", "count": 0, "events": [], "error": str(exc)}


def analyze_risk(params: Dict[str, str] | None = None) -> Dict[str, Any]:
    params = params or {}
    country = params.get("country", "all").lower()
    product = params.get("product", "all").lower()
    days = int(params.get("days", "30") or 30)

    sources = _load_sources()
    poles = DEFAULT_POLES
    if country != "all":
        poles = [p for p in poles if p["country"].lower() == country]
    if product != "all":
        poles = [p for p in poles if any(product in x.lower() for x in p["products"])]
    if not poles:
        poles = DEFAULT_POLES[:4]

    enso = fetch_enso_signal()
    event_query = "fertilizer OR greve OR strike OR drought OR flood OR storm OR tornado OR conflict OR guerra"
    events = fetch_reliefweb_events(event_query, days=90)

    pole_results: List[Dict[str, Any]] = []
    for p in poles[:8]:
        try:
            climate = fetch_nasa_power_point(p["lat"], p["lon"], days=days)
        except Exception as exc:
            climate = {
                "source_status": "fallback_curated",
                "source": "NASA POWER Daily API",
                "error": str(exc),
                "metrics": {"rain_mm": None, "avg_tmax_c": None, "max_wind_ms": None},
                "scores": {"seca": 0, "calor": 0, "vento": 0, "clima": 25},
                "severity": "atenção",
            }
        enso_score = 0
        if enso.get("phase") in ("El Niño", "La Niña") and enso.get("probability"):
            enso_score = _score(float(enso["probability"]), 45, 90)
        disruption_score = min(100, int(events.get("count", 0)) * 8)
        final_score = int(round(0.58 * climate["scores"].get("clima", 0) + 0.22 * enso_score + 0.20 * disruption_score))
        pole_results.append({
            "id": p["id"],
            "name": p["name"],
            "country": p["country"],
            "products": p["products"],
            "risk_score": final_score,
            "severity": _severity(final_score),
            "drivers": {
                "clima": climate["scores"].get("clima", 0),
                "enso": enso_score,
                "eventos_logisticos_sociais": disruption_score,
            },
            "climate": climate,
            "recommended_actions": _actions(final_score, climate, enso, events),
        })

    pole_results.sort(key=lambda x: x["risk_score"], reverse=True)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "ok",
        "method": "regras transparentes + fontes oficiais; sem dado simulado marcado como real",
        "filters": {"country": country, "product": product, "days": days},
        "enso": enso,
        "events": events,
        "poles": pole_results,
        "summary": {
            "max_risk": pole_results[0]["risk_score"] if pole_results else 0,
            "max_severity": pole_results[0]["severity"] if pole_results else "baixo",
            "poles_analyzed": len(pole_results),
            "online_sources": sum(1 for x in [enso, events] if x.get("source_status") == "online_observed")
        },
        "sources": sources["sources"],
        "limitations": [
            "Risco não é previsão determinística de quebra; é triagem antecipatória.",
            "Fertilizantes, guerra e greves exigem confirmação em boletins e notícias oficiais antes de decisão operacional.",
            "NASA POWER é estimativa/reanálise por coordenada, não substitui estação local validada.",
            "ENSO afeta probabilidades regionais, mas não determina sozinho produtividade local."
        ]
    }


def _actions(score: int, climate: Dict[str, Any], enso: Dict[str, Any], events: Dict[str, Any]) -> List[str]:
    actions: List[str] = []
    scores = climate.get("scores", {})
    if scores.get("seca", 0) >= 55:
        actions.append("priorizar checagem de irrigação, disponibilidade hídrica e contrato de compra antecipada")
    if scores.get("calor", 0) >= 55:
        actions.append("monitorar estresse térmico, maturação acelerada e perda pós-colheita")
    if scores.get("vento", 0) >= 55:
        actions.append("verificar risco de dano físico, queda de fruto e interrupção logística")
    if enso.get("phase") in ("El Niño", "La Niña"):
        actions.append(f"acompanhar teleconexões: fase ENSO indicada como {enso.get('phase')}")
    if events.get("count", 0) >= 3:
        actions.append("validar eventos recentes de conflito, greve, enchente ou fertilizante antes de ajustar preço")
    if score >= 75:
        actions.append("emitir alerta vermelho interno e revisar exposição por produto/região")
    if not actions:
        actions.append("manter monitoramento diário; sem gatilho crítico pelos dados atuais")
    return actions
