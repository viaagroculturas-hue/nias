"""NIAS — Route Optimizer API: otimizador logístico agrícola SA."""
import json
import math
import time
from datetime import datetime, timezone

from flv.db import get_conn


MODAL_COSTS = {
    "rodoviario":  {"base_per_km": 0.28, "loading_brl": 800,  "speed_kmh": 60, "perecivel_risk": 0.02},
    "ferroviario": {"base_per_km": 0.14, "loading_brl": 1200, "speed_kmh": 40, "perecivel_risk": 0.005},
    "hidroviario": {"base_per_km": 0.08, "loading_brl": 2000, "speed_kmh": 15, "perecivel_risk": 0.003},
    "multimodal":  {"base_per_km": 0.16, "loading_brl": 1800, "speed_kmh": 35, "perecivel_risk": 0.008},
}

# Valor médio por tonelada por produto (BRL), para cálculo de margem
PRODUCT_VALUES = {
    "soja": 1850, "milho": 900, "tomate": 2200, "cebola": 1500, "batata": 1200,
    "cafe": 18000, "café": 18000, "arroz": 1600, "trigo": 1100, "banana": 1800,
    "default": 2000,
}

# Distâncias (km) entre pares de hubs logísticos
DISTANCES = {
    ("sinop-mt",       "santos-sp"):         {"rodoviario": 1850, "hidroviario": 2100},
    ("sorriso-mt",     "miritituba-pa"):      {"rodoviario": 1100, "hidroviario": 0, "notes": "BR-163→hidrovia Tapajós"},
    ("londrina-pr",    "paranagua-pr"):       {"rodoviario": 150,  "ferroviario": 180},
    ("uberlandia-mg",  "santos-sp"):          {"rodoviario": 780,  "ferroviario": 900},
    ("cascavel-pr",    "santos-sp"):          {"rodoviario": 620,  "ferroviario": 680},
    ("petrolina-pe",   "porto suape-pe"):     {"rodoviario": 560},
    ("santa cruz-bol", "arica-chl"):          {"rodoviario": 800,  "notes": "IIRSA Corredor Bioceânico"},
    ("rosario-arg",    "buenos aires-arg"):   {"rodoviario": 300,  "ferroviario": 290, "hidroviario": 380},
    # Pares por estado (fallback)
    ("mt", "sp"):  {"rodoviario": 1800, "ferroviario": 2100},
    ("mt", "pa"):  {"rodoviario": 1100, "hidroviario": 950},
    ("pr", "sp"):  {"rodoviario": 400,  "ferroviario": 460},
    ("mg", "sp"):  {"rodoviario": 600,  "ferroviario": 680},
    ("go", "sp"):  {"rodoviario": 900,  "ferroviario": 1050},
    ("rs", "sp"):  {"rodoviario": 1150, "ferroviario": 1250},
    ("ba", "sp"):  {"rodoviario": 1500},
    ("pe", "sp"):  {"rodoviario": 2500},
    ("ma", "sp"):  {"rodoviario": 2800},
    ("ms", "sp"):  {"rodoviario": 1000, "ferroviario": 1100},
}


def _normalize(s: str) -> str:
    return (s or "").lower().strip()


def _find_distances(origin: str, destination: str) -> dict:
    """Localiza o melhor par disponível — match exato, depois por estado."""
    o = _normalize(origin)
    d = _normalize(destination)

    # 1. Match exato
    for (ko, kd), v in DISTANCES.items():
        if ko in o and kd in d:
            return dict(v)

    # 2. Extrair UF (2 letras após '-')
    def uf(s):
        parts = s.split("-")
        for p in reversed(parts):
            if len(p) == 2:
                return p
        return s[:2]

    o_uf = uf(o)
    d_uf = uf(d)

    for (ko, kd), v in DISTANCES.items():
        if ko == o_uf and kd == d_uf:
            return dict(v)

    # 3. Fallback genérico
    return {"rodoviario": 1000, "notes": "Distância estimada — par não catalogado"}


def _road_blocked(conn) -> bool:
    try:
        rows = conn.execute(
            "SELECT road_name FROM road_status WHERE status != 'normal' LIMIT 1"
        ).fetchall()
        return len(rows) > 0
    except Exception:
        return False


def _calc_modal(modal: str, dist_km: float, qty: float, blocked_road: bool) -> dict:
    cfg = MODAL_COSTS[modal]
    road_penalty = 1.40 if (modal == "rodoviario" and blocked_road) else 1.0
    cost = (dist_km * cfg["base_per_km"] + cfg["loading_brl"]) * qty * road_penalty
    hours = (dist_km / cfg["speed_kmh"]) * road_penalty
    risk_pct = cfg["perecivel_risk"] * 100
    loss_brl = cost * cfg["perecivel_risk"]
    return {
        "modal": modal,
        "distance_km": round(dist_km, 1),
        "cost_brl": round(cost + loss_brl, 2),
        "hours": round(hours, 1),
        "risk_pct": round(risk_pct, 2),
        "road_penalty_applied": blocked_road and modal == "rodoviario",
    }


def _compute_route(data: dict) -> dict:
    product       = str(data.get("product", "soja"))
    qty           = float(data.get("quantity_tons", 1) or 1)
    origin_city   = str(data.get("origin_city", "") or "")
    origin_state  = str(data.get("origin_state", "") or "")
    dest_city     = str(data.get("destination_city", "") or "")
    dest_state    = str(data.get("destination_state", "") or "")
    priority      = str(data.get("priority", "custo") or "custo").lower()

    origin_key      = f"{origin_city}-{origin_state}".lower() if origin_city else origin_state.lower()
    destination_key = f"{dest_city}-{dest_state}".lower() if dest_city else dest_state.lower()

    conn = get_conn()
    blocked = _road_blocked(conn)
    dists = _find_distances(origin_key, destination_key)
    notes_from_data = dists.pop("notes", None)

    options = []
    for modal, dist_km in dists.items():
        if modal == "notes":
            continue
        if dist_km is None or dist_km == 0:
            continue
        options.append(_calc_modal(modal, float(dist_km), qty, blocked))

    if not options:
        options.append(_calc_modal("rodoviario", 1000, qty, blocked))

    # Ordenação por prioridade
    if priority == "tempo":
        options.sort(key=lambda x: x["hours"])
    elif priority == "segurança":
        options.sort(key=lambda x: x["risk_pct"])
    else:  # custo
        options.sort(key=lambda x: x["cost_brl"])

    best = options[0]
    rest = options[1:]

    prod_val = PRODUCT_VALUES.get(_normalize(product), PRODUCT_VALUES["default"])
    cargo_value = prod_val * qty
    margin_impact = round(best["cost_brl"] / cargo_value, 4) if cargo_value > 0 else 0

    warnings = []
    if blocked:
        warnings.append("Bloqueio rodoviário ativo detectado no DB — modal rodoviário com custo penalizado em +40%.")
    if notes_from_data:
        warnings.append(notes_from_data)

    return {
        "origin": origin_key,
        "destination": destination_key,
        "product": product,
        "quantity_tons": qty,
        "priority": priority,
        "recommended_route": best,
        "alternatives": rest,
        "route_warnings": warnings,
        "estimated_margin_impact": margin_impact,
        "cargo_value_estimate_brl": round(cargo_value, 2),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Handler ──────────────────────────────────────────────────────────────────

def handle_route_optimizer(handler, path):
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body = handler.rfile.read(length) if length else b"{}"
        data = json.loads(body or b"{}")
        result = _compute_route(data)
        out = json.dumps(result, ensure_ascii=False).encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(out)
    except Exception as e:
        err = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(err)
