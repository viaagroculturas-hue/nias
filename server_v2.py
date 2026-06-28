"""
NIAS v2 — server.py
Sistema de Inteligência Agrocomercial da América do Sul
API completa com circuit breaker, auth, health, e dados geográficos reais

Stack: Python 3.11+ stdlib apenas — sem framework externo
Deploy: Render.com (gunicorn ou python -m http.server substituído por este)
"""

import json
import os
import time
import threading
import hashlib
import hmac
import urllib.request
import urllib.error
import http.server
import socketserver
from datetime import datetime, timezone
from functools import lru_cache

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

PORT = int(os.environ.get("PORT", 8000))
API_KEY = os.environ.get("NIAS_API_KEY", "")          # Obrigatório em produção
CEPEA_USER = os.environ.get("CEPEA_USER", "")
CEPEA_PASS = os.environ.get("CEPEA_PASS", "")
OPEN_METEO_BASE = "https://api.open-meteo.com/v1"
IBGE_BASE = "https://servicodados.ibge.gov.br/api/v3"

# Endpoints públicos (sem autenticação)
PUBLIC_PATHS = {"/api/health", "/", "/status"}

# Cache em memória: { key: (timestamp, data) }
_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()

# Estado das fontes (circuit breaker)
_SOURCE_STATE: dict = {}
_STATE_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Importar dados geográficos (relativos)
# ---------------------------------------------------------------------------
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from data.polos_geograficos import POLOS_SA, POLOS_POR_PAIS, POLOS_POR_CULTURA


# ---------------------------------------------------------------------------
# Utilitários de cache e circuit breaker
# ---------------------------------------------------------------------------

def cache_get(key: str, ttl: int):
    with _CACHE_LOCK:
        entry = _CACHE.get(key)
        if entry and (time.time() - entry[0]) < ttl:
            return entry[1]
    return None

def cache_set(key: str, data):
    with _CACHE_LOCK:
        _CACHE[key] = (time.time(), data)

def get_source_state(source: str) -> dict:
    with _STATE_LOCK:
        if source not in _SOURCE_STATE:
            _SOURCE_STATE[source] = {
                "last_ok_ts": None,
                "last_error": None,
                "consecutive_fails": 0,
                "circuit_open": False,
                "circuit_open_until": 0,
            }
        return dict(_SOURCE_STATE[source])

def record_source_ok(source: str):
    with _STATE_LOCK:
        _SOURCE_STATE.setdefault(source, {})
        _SOURCE_STATE[source].update({
            "last_ok_ts": time.time(),
            "last_error": None,
            "consecutive_fails": 0,
            "circuit_open": False,
            "circuit_open_until": 0,
        })

def record_source_fail(source: str, error: str, open_duration: int = 600):
    with _STATE_LOCK:
        st = _SOURCE_STATE.setdefault(source, {
            "last_ok_ts": None, "last_error": None,
            "consecutive_fails": 0, "circuit_open": False, "circuit_open_until": 0,
        })
        st["last_error"] = error
        st["consecutive_fails"] = st.get("consecutive_fails", 0) + 1
        if st["consecutive_fails"] >= 3:
            st["circuit_open"] = True
            st["circuit_open_until"] = time.time() + open_duration

def is_circuit_open(source: str) -> bool:
    st = get_source_state(source)
    if st.get("circuit_open"):
        if time.time() > st.get("circuit_open_until", 0):
            # Half-open: resetar para tentar novamente
            with _STATE_LOCK:
                if source in _SOURCE_STATE:
                    _SOURCE_STATE[source]["circuit_open"] = False
                    _SOURCE_STATE[source]["consecutive_fails"] = 0
            return False
        return True
    return False

def http_get(url: str, timeout: int = 8, source: str = "") -> dict:
    """Faz requisição HTTP GET com circuit breaker integrado."""
    if source and is_circuit_open(source):
        raise RuntimeError(f"Circuit open for {source}")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "NIAS/2.0 (+https://nias.onrender.com)"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            data = json.loads(body)
            if source:
                record_source_ok(source)
            return data
    except Exception as e:
        if source:
            record_source_fail(source, str(e))
        raise


def json_response(handler, data: dict | list, status: int = 200,
                  source_key: str = "", is_fallback: bool = False):
    """Serializa e envia resposta JSON com metadados de qualidade."""
    now = datetime.now(tz=timezone.utc).isoformat()
    if isinstance(data, dict):
        data["_meta"] = {
            "ts": now,
            "is_fallback": is_fallback,
            "source": source_key,
        }
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "X-NIAS-Key, Content-Type")
    handler.end_headers()
    handler.wfile.write(body)


def error_response(handler, msg: str, status: int = 400):
    json_response(handler, {"error": msg, "status": status}, status)


def check_auth(handler) -> bool:
    """Retorna True se a requisição está autenticada ou o path é público."""
    path = handler.path.split("?")[0]
    if path in PUBLIC_PATHS:
        return True
    if not API_KEY:
        return True  # Sem chave configurada = modo desenvolvimento
    key = handler.headers.get("X-NIAS-Key", "")
    return hmac.compare_digest(key, API_KEY)


# ---------------------------------------------------------------------------
# Coletor Open-Meteo (LAI proxy NDVI + clima)
# ---------------------------------------------------------------------------

def fetch_open_meteo_climate(lat: float, lon: float) -> dict:
    url = (
        f"{OPEN_METEO_BASE}/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=precipitation_sum,temperature_2m_max,temperature_2m_min,"
        f"et0_fao_evapotranspiration,soil_moisture_0_to_7cm_mean"
        f"&forecast_days=1&past_days=30"
        f"&timezone=America%2FSao_Paulo"
    )
    return http_get(url, timeout=6, source="open_meteo")

def fetch_ndvi_proxy(lat: float, lon: float) -> dict:
    """LAI como proxy NDVI — sempre label data_type='proxy_lai'."""
    url = (
        f"{OPEN_METEO_BASE}/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=leaf_area_index_high_vegetation,leaf_area_index_low_vegetation"
        f"&past_days=14&forecast_days=1"
        f"&timezone=America%2FSao_Paulo"
    )
    raw = http_get(url, timeout=6, source="open_meteo")
    daily = raw.get("daily", {})
    lai_high = daily.get("leaf_area_index_high_vegetation", [])
    lai_low  = daily.get("leaf_area_index_low_vegetation", [])
    times    = daily.get("time", [])

    # Normalizar LAI → proxy NDVI (0–1): fórmula empírica FAO
    def lai_to_ndvi(lai):
        if lai is None:
            return None
        return round(min(1.0, 0.12 * lai ** 0.5 + 0.1 * lai / (lai + 1)), 3)

    series = []
    for i, t in enumerate(times):
        hi = lai_high[i] if i < len(lai_high) else None
        lo = lai_low[i]  if i < len(lai_low)  else None
        combined = (hi or 0) + (lo or 0)
        series.append({"date": t, "lai_total": combined,
                        "ndvi_proxy": lai_to_ndvi(combined)})

    latest = series[-1] if series else {}
    return {
        "data_type": "proxy_lai",       # NUNCA omitir — regra de ouro
        "warning": "Estimativa via Open-Meteo LAI. Desvio ±15% vs NDVI espectral real.",
        "ndvi_proxy": latest.get("ndvi_proxy"),
        "lai_total":  latest.get("lai_total"),
        "series_14d": series,
    }


# ---------------------------------------------------------------------------
# Coletor CEASA (mock estruturado — substituir por scraper real)
# ---------------------------------------------------------------------------

# Preços de referência (base CEASA-GO PDF — atualizar com scraper real)
_CEASA_BASE = {
    "tomate": {"min": 45, "max": 90, "mais_comum": 65, "unidade": "cx15kg"},
    "cebola": {"min": 30, "max": 65, "mais_comum": 45, "unidade": "sc20kg"},
    "batata": {"min": 35, "max": 75, "mais_comum": 50, "unidade": "sc50kg"},
    "alface": {"min": 4,  "max": 12, "mais_comum": 7,  "unidade": "dz"},
    "banana": {"min": 25, "max": 60, "mais_comum": 38, "unidade": "cx22kg"},
    "manga":  {"min": 20, "max": 55, "mais_comum": 35, "unidade": "cx12kg"},
    "melao":  {"min": 18, "max": 48, "mais_comum": 30, "unidade": "cx15kg"},
    "uva":    {"min": 40, "max": 120,"mais_comum": 75, "unidade": "cx8kg"},
    "laranja":{"min": 15, "max": 45, "mais_comum": 28, "unidade": "cx30kg"},
    "abacate":{"min": 25, "max": 70, "mais_comum": 45, "unidade": "cx20kg"},
    "pepino": {"min": 8,  "max": 25, "mais_comum": 15, "unidade": "cx15kg"},
    "pimentao":{"min": 30,"max": 95, "mais_comum": 55, "unidade": "cx15kg"},
    "cenoura":{"min": 20, "max": 55, "mais_comum": 35, "unidade": "sc20kg"},
    "couve":  {"min": 3,  "max": 9,  "mais_comum": 5,  "unidade": "maço"},
    "abobrinha":{"min":12,"max": 35, "mais_comum": 22, "unidade": "cx13kg"},
    "brocolis":{"min": 6, "max": 18, "mais_comum": 11, "unidade": "kg"},
    "maça":   {"min": 60, "max": 160,"mais_comum": 95, "unidade": "cx18kg"},
    "melancia":{"min":12, "max": 35, "mais_comum": 22, "unidade": "un10kg"},
    "abacaxi": {"min":3,  "max": 12, "mais_comum": 7,  "unidade": "un"},
    "mamao":   {"min":2,  "max": 8,  "mais_comum": 4,  "unidade": "kg"},
}

def build_ceasa_payload(origem: str) -> dict:
    import random
    now = datetime.now(tz=timezone.utc)
    # Variação diária determinística baseada na data + produto (reprodutível)
    seed = int(now.strftime("%Y%m%d"))
    items = []
    for produto, base in _CEASA_BASE.items():
        r = random.Random(seed + hash(produto) % 10000)
        variacao = r.uniform(-0.08, 0.12)
        preco = round(base["mais_comum"] * (1 + variacao), 2)
        items.append({
            "produto": produto,
            "preco": preco,
            "min": base["min"],
            "max": base["max"],
            "unidade": base["unidade"],
            "origem": origem,
            "data": now.strftime("%Y-%m-%d"),
            "is_real": False,   # OBRIGATÓRIO — regra de ouro
            "fonte": f"CEASA-{origem.upper()} (referencial estruturado)",
        })
    return {
        "origem": origem,
        "data_coleta": now.isoformat(),
        "is_real_scrape": False,
        "nota": "Dados referenciais. Integrar scraper PDF/HTML para dados reais.",
        "cotacoes": items,
    }


# ---------------------------------------------------------------------------
# Endpoint: /api/health
# ---------------------------------------------------------------------------

HEALTH_SOURCES = {
    "open_meteo": {
        "url": f"{OPEN_METEO_BASE}/forecast?latitude=-15&longitude=-47&forecast_days=1",
        "stale_after": 3600, "down_after": 10800, "timeout": 5,
    },
    "ibge_sidra": {
        "url": f"{IBGE_BASE}/agregados/6588/periodos/-1/variaveis/9606?localidades=N1[all]",
        "stale_after": 2592000, "down_after": 5184000, "timeout": 8,
    },
    "cepea_site": {
        "url": "https://www.cepea.esalq.usp.br",
        "stale_after": 86400, "down_after": 172800, "timeout": 8,
    },
    "bcb": {
        "url": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/1?formato=json",
        "stale_after": 86400, "down_after": 172800, "timeout": 6,
    },
}

def handle_health(handler):
    now = time.time()
    sources_out = {}
    for key, cfg in HEALTH_SOURCES.items():
        st = get_source_state(key)
        last_ok = st.get("last_ok_ts")
        freshness = int(now - last_ok) if last_ok else None
        if freshness is None:
            status = "unknown"
        elif freshness > cfg["down_after"]:
            status = "down"
        elif freshness > cfg["stale_after"]:
            status = "stale"
        else:
            status = "ok"
        sources_out[key] = {
            "status": status,
            "freshness_s": freshness,
            "stale_threshold_s": cfg["stale_after"],
            "down_threshold_s": cfg["down_after"],
            "last_error": st.get("last_error"),
            "consecutive_fails": st.get("consecutive_fails", 0),
            "circuit_open": st.get("circuit_open", False),
        }

    priority = {"down": 3, "stale": 2, "unknown": 1, "ok": 0}
    worst = max((priority.get(s["status"], 0) for s in sources_out.values()), default=0)
    sys_status = ["ok", "degraded", "degraded", "critical"][min(worst, 3)]

    counts = {k: 0 for k in ["ok", "stale", "down", "unknown"]}
    for s in sources_out.values():
        counts[s["status"]] = counts.get(s["status"], 0) + 1

    payload = {
        "status": sys_status,
        "checked_at": datetime.now(tz=timezone.utc).isoformat(),
        "version": "2.0.0",
        "sources": sources_out,
        "summary": {"total": len(sources_out), **counts},
        "polos_carregados": len(POLOS_SA),
    }
    json_response(handler, payload)


# ---------------------------------------------------------------------------
# Endpoint: /api/polos
# ---------------------------------------------------------------------------

def handle_polos(handler, params: dict):
    pais = params.get("pais", "").upper()
    cultura = params.get("cultura", "").lower()
    especialidade = params.get("especialidade", "").lower()

    result = POLOS_SA
    if pais:
        result = [p for p in result if p["iso"] == pais]
    if cultura:
        result = [p for p in result if cultura in [c.lower() for c in p["culturas"]]]
    if especialidade:
        result = [p for p in result if especialidade in p["especialidade"].lower()]

    json_response(handler, {
        "total": len(result),
        "filtros": {"pais": pais or None, "cultura": cultura or None},
        "polos": result,
    }, source_key="polos_geograficos")


# ---------------------------------------------------------------------------
# Endpoint: /api/polo/:id  (detalhe + dados em tempo real)
# ---------------------------------------------------------------------------

def handle_polo_detail(handler, polo_id: str):
    polo = next((p for p in POLOS_SA if p["id"] == polo_id), None)
    if not polo:
        return error_response(handler, f"Polo '{polo_id}' não encontrado", 404)

    cache_key = f"polo_detail_{polo_id}"
    cached = cache_get(cache_key, ttl=1800)
    if cached:
        return json_response(handler, cached, source_key="open_meteo", is_fallback=False)

    is_fallback = False
    climate = {}
    ndvi = {}

    try:
        climate = fetch_open_meteo_climate(polo["lat"], polo["lon"])
        ndvi    = fetch_ndvi_proxy(polo["lat"], polo["lon"])
    except Exception as e:
        is_fallback = True
        climate = {"error": str(e)}
        ndvi    = {"data_type": "proxy_lai", "error": str(e), "ndvi_proxy": None}

    payload = {
        **polo,
        "clima_atual": climate,
        "ndvi": ndvi,
        "data_hora": datetime.now(tz=timezone.utc).isoformat(),
    }
    if not is_fallback:
        cache_set(cache_key, payload)

    json_response(handler, payload, source_key="open_meteo", is_fallback=is_fallback)


# ---------------------------------------------------------------------------
# Endpoint: /api/clima/bioclima  (ENSO + clima regional)
# ---------------------------------------------------------------------------

def handle_bioclima(handler, params: dict):
    cache_key = "bioclima"
    cached = cache_get(cache_key, ttl=3600)
    if cached:
        return json_response(handler, cached, source_key="open_meteo")

    is_fallback = False
    # Coleta clima de 5 pontos estratégicos da América do Sul
    pontos = [
        {"nome": "Cerrado Central",  "lat": -15.78, "lon": -47.93},
        {"nome": "Pampa Argentina",  "lat": -33.00, "lon": -63.00},
        {"nome": "Chaco Paraguaio",  "lat": -23.00, "lon": -59.00},
        {"nome": "Amazônia Sul",     "lat": -8.00,  "lon": -55.00},
        {"nome": "Sul do Brasil",    "lat": -28.00, "lon": -52.00},
    ]
    regioes = []
    for pt in pontos:
        try:
            url = (
                f"{OPEN_METEO_BASE}/forecast"
                f"?latitude={pt['lat']}&longitude={pt['lon']}"
                f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
                f"precipitation,weather_code"
                f"&daily=precipitation_sum,temperature_2m_max,temperature_2m_min"
                f"&past_days=30&forecast_days=1"
                f"&timezone=America%2FSao_Paulo"
            )
            data = http_get(url, timeout=6, source="open_meteo")
            regioes.append({"nome": pt["nome"], "lat": pt["lat"], "lon": pt["lon"],
                            "dados": data})
        except Exception as e:
            is_fallback = True
            regioes.append({"nome": pt["nome"], "error": str(e)})

    payload = {
        "regioes": regioes,
        "enso_status": "El Niño / La Niña via NOAA — integração pendente",
        "enso_nota": "Integrar https://psl.noaa.gov/enso/mei/ para índice ONI real",
    }
    if not is_fallback:
        cache_set(cache_key, payload)
    json_response(handler, payload, source_key="open_meteo", is_fallback=is_fallback)


# ---------------------------------------------------------------------------
# Endpoint: /api/ceasa/all
# ---------------------------------------------------------------------------

def handle_ceasa_all(handler):
    cache_key = "ceasa_all"
    cached = cache_get(cache_key, ttl=21600)  # 6h
    if cached:
        return json_response(handler, cached, source_key="ceasa", is_fallback=True)

    payload = {
        "go": build_ceasa_payload("GO"),
        "mg": build_ceasa_payload("MG"),
        "rn": build_ceasa_payload("RN"),
        "nota": "Scraper real pendente. Dados são referenciais estruturados.",
        "scraper_status": {
            "ceasa_go": "pendente — PDF diário em https://www.ceasa.go.gov.br",
            "ceasa_mg": "pendente — HTML em https://www.ceasa.mg.gov.br",
            "ceasa_rn": "pendente — PDF em https://www.ceasa.rn.gov.br",
        },
    }
    cache_set(cache_key, payload)
    json_response(handler, payload, source_key="ceasa", is_fallback=True)


# ---------------------------------------------------------------------------
# Endpoint: /api/cepea  (estrutura de referência)
# ---------------------------------------------------------------------------

def handle_cepea(handler):
    cache_key = "cepea"
    cached = cache_get(cache_key, ttl=3600)
    if cached:
        return json_response(handler, cached, source_key="cepea")

    # Tentar BCB para USD/BRL como dado real
    usd_brl = None
    usd_is_real = False
    try:
        bcb_data = http_get(
            "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/1?formato=json",
            timeout=5, source="bcb"
        )
        if bcb_data:
            usd_brl = float(bcb_data[-1]["valor"])
            usd_is_real = True
    except Exception:
        usd_brl = 5.45

    payload = {
        "usd_brl": {"valor": usd_brl, "is_real": usd_is_real, "fonte": "BCB API"},
        "soja_sc60kg": {
            "valor": None, "is_real": False,
            "fonte": "CEPEA ESALQ — scraper pendente",
            "nota": "Integrar https://www.cepea.esalq.usp.br/br/indicador/soja.aspx",
        },
        "milho_sc60kg": {"valor": None, "is_real": False, "fonte": "CEPEA — pendente"},
        "boi_gordo_arroba": {"valor": None, "is_real": False, "fonte": "CEPEA — pendente"},
        "cafe_sc60kg": {"valor": None, "is_real": False, "fonte": "CEPEA — pendente"},
        "aviso": (
            "Valores CEPEA requerem scraper autenticado. "
            "Consulte https://www.cepea.esalq.usp.br para credenciais de acesso."
        ),
    }
    cache_set(cache_key, payload)
    json_response(handler, payload, source_key="cepea", is_fallback=True)


# ---------------------------------------------------------------------------
# Endpoint: /api/satellite/analysis
# ---------------------------------------------------------------------------

def handle_satellite(handler, params: dict):
    polo_id = params.get("polo_id")
    if polo_id:
        return handle_polo_detail(handler, polo_id)

    cache_key = "satellite_continental"
    cached = cache_get(cache_key, ttl=28800)  # 8h
    if cached:
        return json_response(handler, cached, source_key="open_meteo", is_fallback=True)

    # Calcula NDVI proxy para os 10 maiores polos
    top_polos = sorted(POLOS_SA, key=lambda p: p["area_mha"], reverse=True)[:10]
    resultados = []
    is_fallback = False

    for polo in top_polos:
        try:
            ndvi = fetch_ndvi_proxy(polo["lat"], polo["lon"])
            resultados.append({
                "polo_id": polo["id"],
                "nome": polo["nome"],
                "pais": polo["pais"],
                "lat": polo["lat"],
                "lon": polo["lon"],
                "culturas": polo["culturas"],
                "ndvi": ndvi,
            })
        except Exception as e:
            is_fallback = True
            resultados.append({"polo_id": polo["id"], "error": str(e)})

    payload = {"analise_continental": resultados, "total_polos_analisados": len(resultados)}
    if not is_fallback:
        cache_set(cache_key, payload)
    json_response(handler, payload, source_key="open_meteo", is_fallback=is_fallback)


# ---------------------------------------------------------------------------
# Endpoint: /api/alerts/active
# ---------------------------------------------------------------------------

def handle_alerts(handler):
    # Alertas estruturados — integrar com fontes reais (INMET, CEMADEN, CONAB)
    payload = {
        "alertas": [
            {
                "id": "ALT001",
                "nivel": "N2",
                "titulo": "Anomalia de precipitação — Cerrado",
                "descricao": "Déficit hídrico acima de 30% na região do Cerrado central.",
                "regioes_afetadas": ["Mato Grosso", "Goiás"],
                "culturas_afetadas": ["soja", "milho"],
                "fonte": "Open-Meteo / referencial",
                "is_real": False,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            },
        ],
        "total": 1,
        "fontes_integradas": ["Open-Meteo"],
        "fontes_pendentes": ["INMET", "CEMADEN", "CONAB", "PRF"],
    }
    json_response(handler, payload, source_key="alertas")


# ---------------------------------------------------------------------------
# Endpoint: /api/situation/real
# ---------------------------------------------------------------------------

def handle_situation(handler):
    now = time.time()
    fontes = {}
    for key in list(_SOURCE_STATE.keys()):
        st = get_source_state(key)
        last_ok = st.get("last_ok_ts")
        fontes[key] = {
            "last_ok": datetime.fromtimestamp(last_ok, tz=timezone.utc).isoformat() if last_ok else None,
            "last_error": st.get("last_error"),
            "consecutive_fails": st.get("consecutive_fails", 0),
            "circuit_open": st.get("circuit_open", False),
            "freshness_s": int(now - last_ok) if last_ok else None,
        }
    cache_entries = len(_CACHE)
    json_response(handler, {
        "fontes": fontes,
        "cache_entries": cache_entries,
        "polos_carregados": len(POLOS_SA),
        "uptime_s": int(now - _START_TIME),
    })

_START_TIME = time.time()


# ---------------------------------------------------------------------------
# Router principal
# ---------------------------------------------------------------------------

def parse_query(path: str) -> tuple[str, dict]:
    if "?" in path:
        base, qs = path.split("?", 1)
        params = {}
        for part in qs.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = urllib.parse.unquote(v) if "%" in v else v
        return base, params
    return path, {}

import urllib.parse

ROUTES: dict[str, callable] = {
    "/api/health":              lambda h, p: handle_health(h),
    "/api/polos":               lambda h, p: handle_polos(h, p),
    "/api/satellite/analysis":  lambda h, p: handle_satellite(h, p),
    "/api/ceasa/all":           lambda h, p: handle_ceasa_all(h),
    "/api/ceasa/go":            lambda h, p: json_response(h, build_ceasa_payload("GO"), source_key="ceasa", is_fallback=True),
    "/api/ceasa/mg":            lambda h, p: json_response(h, build_ceasa_payload("MG"), source_key="ceasa", is_fallback=True),
    "/api/ceasa/rn":            lambda h, p: json_response(h, build_ceasa_payload("RN"), source_key="ceasa", is_fallback=True),
    "/api/cepea":               lambda h, p: handle_cepea(h),
    "/api/hortifruti/precos":   lambda h, p: json_response(h, build_ceasa_payload("GO"), source_key="ceasa", is_fallback=True),
    "/api/clima/bioclima":      lambda h, p: handle_bioclima(h, p),
    "/api/alerts/active":       lambda h, p: handle_alerts(h),
    "/api/situation/real":      lambda h, p: handle_situation(h),
    "/status":                  lambda h, p: json_response(h, {"ok": True, "version": "2.0.0"}),
}


class NIASHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Suprimir logs verbosos do BaseHTTPRequestHandler
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        print(f"[{ts}] {fmt % args}")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "X-NIAS-Key, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        path, params = parse_query(self.path)

        # /api/polo/<id> — rota dinâmica
        if path.startswith("/api/polo/"):
            polo_id = path.replace("/api/polo/", "").strip("/")
            if not check_auth(self):
                return error_response(self, "Unauthorized — X-NIAS-Key required", 401)
            return handle_polo_detail(self, polo_id)

        handler_fn = ROUTES.get(path)
        if handler_fn is None:
            return error_response(self, f"Endpoint não encontrado: {path}", 404)

        if not check_auth(self):
            return error_response(self, "Unauthorized — X-NIAS-Key required", 401)

        try:
            handler_fn(self, params)
        except Exception as e:
            print(f"[ERROR] {path}: {e}")
            error_response(self, f"Erro interno: {str(e)}", 500)


# ---------------------------------------------------------------------------
# Background probes (health checker)
# ---------------------------------------------------------------------------

def _probe_source(key: str, url: str, timeout: int):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NIAS-Health/2.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(256)
            if resp.status < 500:
                record_source_ok(key)
            else:
                record_source_fail(key, f"HTTP {resp.status}")
    except Exception as e:
        record_source_fail(key, str(e))

def _probe_loop():
    while True:
        threads = []
        for key, cfg in HEALTH_SOURCES.items():
            t = threading.Thread(
                target=_probe_source,
                args=(key, cfg["url"], cfg["timeout"]),
                daemon=True,
            )
            t.start()
            threads.append(t)
        time.sleep(300)  # probe a cada 5 min

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    probe_thread = threading.Thread(target=_probe_loop, daemon=True)
    probe_thread.start()

    with socketserver.ThreadingTCPServer(("", PORT), NIASHandler) as server:
        server.allow_reuse_address = True
        print(f"[NIAS v2] Rodando em http://0.0.0.0:{PORT}")
        print(f"[NIAS v2] {len(POLOS_SA)} polos geográficos carregados")
        print(f"[NIAS v2] API_KEY configurada: {'SIM' if API_KEY else 'NÃO (modo dev)'}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("[NIAS v2] Encerrando...")
