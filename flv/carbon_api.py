"""NIAS — Carbon API: calculadora de pegada de carbono por lote agrícola."""
import json
import math
from datetime import datetime, timezone

from flv.db import get_conn


EMISSION_FACTORS = {
    "producao": {
        "soja":    0.45, "milho":   0.38, "tomate": 0.28,
        "cebola":  0.22, "batata":  0.25, "banana": 0.20,
        "arroz":   1.85, "cafe":    0.55, "café":   0.55,
        "trigo":   0.42, "feijao":  0.48, "feijão": 0.48,
        "mandioca": 0.30, "laranja": 0.18, "uva":   0.35,
        "default": 0.35,
    },
    "transporte": {
        "rodoviario":  0.092,   # kgCO2e por ton.km
        "ferroviario": 0.028,
        "hidroviario": 0.019,
    },
    "armazenagem": {
        "refrigerado": 0.04,    # kgCO2e por ton por dia
        "seco":        0.008,
        "ambient":     0.002,
    },
    "organico_reducao": 0.35,   # -35% se produto orgânico
}

# Uma árvore sequestra ~21 kgCO2 por ano
TREE_SEQ_KG_YEAR = 21.0

# Produtos perecíveis (refrigerado), demais = seco
REFRIGERATED_PRODUCTS = {
    "tomate", "alface", "folha", "morango", "uva", "banana",
    "laranja", "limao", "limão", "manga", "maçã", "maca",
    "pepino", "pimentão", "pimentao", "brócolis", "brocolis",
}


def _storage_type(product: str) -> str:
    p = product.lower()
    if any(r in p for r in REFRIGERATED_PRODUCTS):
        return "refrigerado"
    return "seco"


def _production_factor(product: str) -> float:
    p = product.lower()
    factors = EMISSION_FACTORS["producao"]
    if p in factors:
        return factors[p]
    # Fuzzy match
    for k, v in factors.items():
        if k in p or p in k:
            return v
    return factors["default"]


def _classify(total_kg: float) -> str:
    if total_kg < 50:
        return "baixo"
    elif total_kg < 150:
        return "medio"
    elif total_kg < 500:
        return "alto"
    else:
        return "critico"


def _reduction_tips(em: dict, organic: bool) -> list:
    tips = []
    if em["transporte"] > em["producao"]:
        tips.append("Transporte é o maior emissor — considere modal ferroviário ou hidroviário para reduzir em até 70%.")
    if not organic:
        tips.append("Certificação orgânica pode reduzir a emissão de produção em 35%.")
    if em["armazenagem"] > 50:
        tips.append("Reduzir tempo de armazenagem refrigerada ou migrar para armazéns secos quando possível.")
    if em["total"] > 500:
        tips.append("Emissão crítica — considere programa de compensação (créditos de carbono) para neutralizar o lote.")
    if em["per_ton"] > 100:
        tips.append("Emissão por tonelada acima de 100 kgCO2e — lote não elegível para certificação ESG padrão.")
    if not tips:
        tips.append("Lote com pegada baixa — mantenha práticas atuais e documente para certificação ESG.")
    return tips


def _lookup_lot(lot_id: str) -> dict | None:
    """Tenta buscar dados do lote no DB."""
    if not lot_id:
        return None
    conn = get_conn()
    tables = [
        ("lots",    "lot_id",  "product", "quantity_tons", "origin_state", "transport_km", "storage_days"),
        ("lotes",   "id",      "produto", "quantidade_ton", "estado_origem", "km_transporte", "dias_armazenagem"),
    ]
    for tbl, id_col, p_col, q_col, o_col, km_col, sd_col in tables:
        try:
            row = conn.execute(
                f"SELECT {p_col},{q_col},{o_col},{km_col},{sd_col} FROM {tbl} WHERE {id_col}=? LIMIT 1",
                (lot_id,)
            ).fetchone()
            if row:
                return {
                    "product":      row[0],
                    "quantity_tons": float(row[1] or 1),
                    "origin_state": row[2] or "",
                    "transport_km": float(row[3] or 500),
                    "storage_days": int(row[4] or 7),
                    "organic":      False,
                }
        except Exception:
            continue
    return None


def _compute_carbon(data: dict) -> dict:
    lot_id       = str(data.get("lot_id", "") or "")
    product      = str(data.get("product", "soja") or "soja")
    qty          = float(data.get("quantity_tons", 1) or 1)
    origin_state = str(data.get("origin_state", "") or "")
    dest_state   = str(data.get("destination_state", "") or "")
    transport_km = float(data.get("transport_km", 500) or 500)
    storage_days = int(data.get("storage_days", 7) or 7)
    organic      = bool(data.get("organic", False))

    # Se lot_id fornecido, tenta sobrepor com dados do DB
    if lot_id:
        lot_data = _lookup_lot(lot_id)
        if lot_data:
            product      = lot_data.get("product", product)
            qty          = lot_data.get("quantity_tons", qty)
            origin_state = lot_data.get("origin_state", origin_state)
            transport_km = lot_data.get("transport_km", transport_km)
            storage_days = lot_data.get("storage_days", storage_days)
            organic      = lot_data.get("organic", organic)

    # Fase 1: produção
    prod_factor  = _production_factor(product)
    em_producao  = qty * prod_factor
    if organic:
        em_producao *= (1 - EMISSION_FACTORS["organico_reducao"])

    # Fase 2: transporte (rodoviário como padrão)
    em_transporte = qty * transport_km * EMISSION_FACTORS["transporte"]["rodoviario"]

    # Fase 3: armazenagem
    stor_type    = _storage_type(product)
    em_armazenagem = qty * storage_days * EMISSION_FACTORS["armazenagem"][stor_type]

    em_total = em_producao + em_transporte + em_armazenagem
    per_ton  = em_total / qty if qty else 0

    trees    = math.ceil(em_total / TREE_SEQ_KG_YEAR)
    classif  = _classify(em_total)
    cert_ok  = per_ton < 100

    em_dict = {
        "producao":    round(em_producao, 3),
        "transporte":  round(em_transporte, 3),
        "armazenagem": round(em_armazenagem, 3),
        "total":       round(em_total, 3),
    }

    return {
        "lot_id":             lot_id or "N/A",
        "product":            product,
        "quantity_tons":      qty,
        "origin_state":       origin_state,
        "destination_state":  dest_state,
        "transport_km":       transport_km,
        "storage_days":       storage_days,
        "storage_type":       stor_type,
        "organic":            organic,
        "emissions":          em_dict,
        "unit":               "kgCO2e",
        "per_ton":            round(per_ton, 3),
        "trees_equivalent":   trees,
        "classification":     classif,
        "certification_ready": cert_ok,
        "reduction_tips":     _reduction_tips(em_dict, organic),
        "generated_at":       datetime.now(timezone.utc).isoformat(),
    }


# ─── Handler ──────────────────────────────────────────────────────────────────

def handle_carbon(handler, path):
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(path)
        qs     = parse_qs(parsed.query)
        method = handler.command if hasattr(handler, "command") else "GET"

        if method == "POST":
            length = int(handler.headers.get("Content-Length", 0))
            body   = handler.rfile.read(length) if length else b"{}"
            data   = json.loads(body or b"{}")
        else:
            data = {
                "lot_id":       qs.get("lot_id", [""])[0],
                "product":      qs.get("product", ["soja"])[0],
                "quantity_tons": float(qs.get("quantity_tons", [100])[0]),
                "transport_km": float(qs.get("transport_km", [500])[0]),
                "storage_days": int(qs.get("storage_days", [7])[0]),
                "organic":      qs.get("organic", ["false"])[0].lower() == "true",
                "origin_state": qs.get("origin_state", [""])[0],
                "destination_state": qs.get("destination_state", [""])[0],
            }

        result = _compute_carbon(data)
        out    = json.dumps(result, ensure_ascii=False).encode("utf-8")
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
