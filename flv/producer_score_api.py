"""NIAS — Producer Score API: Score Soberano do Produtor (0-1000)."""
import json
import os
from datetime import datetime, timezone

from flv.db import get_conn


# ─── Tabelas de pontuação ──────────────────────────────────────────────────────

def _score_escala(area_ha: float) -> tuple:
    """Dimensão 1 — Escala de produção (0-200)."""
    if area_ha < 50:
        pts, label = 40, "Minifúndio (<50 ha)"
    elif area_ha < 200:
        pts, label = 80, "Pequeno (50-200 ha)"
    elif area_ha < 1000:
        pts, label = 130, "Médio (200-1000 ha)"
    elif area_ha < 5000:
        pts, label = 170, "Grande (1000-5000 ha)"
    else:
        pts, label = 200, "Latifúndio (>5000 ha)"
    return pts, label


def _score_cultura(culture: str) -> tuple:
    """Dimensão 2 — Cultura e mercado (0-150)."""
    c = (culture or "").lower()
    if any(x in c for x in ["café", "cafe", "arabica", "arábica", "vitis", "uva", "vinho"]):
        pts, label = 150, "Café arábica / viticultura premium"
    elif any(x in c for x in ["soja", "milho", "corn", "soybean"]):
        pts, label = 130, "Soja/milho exportação"
    elif any(x in c for x in ["tomate", "alface", "folha", "hortaliça", "hortalica", "pimentão", "morango"]):
        pts, label = 120, "Hortaliças premium"
    else:
        pts, label = 90, "Grãos básicos / outros"
    return pts, label


def _score_zona(state: str) -> tuple:
    """Dimensão 3 — Zona agroclimática (0-150)."""
    s = (state or "").upper()
    if s in ("RS", "SC"):
        pts, label = 150, "Sul — alta regularidade hídrica"
    elif s in ("PR", "SP"):
        pts, label = 130, "Sudeste/Sul — boa regularidade"
    elif s in ("GO", "MG"):
        pts, label = 110, "Centro/Sudeste — bom potencial"
    elif s in ("MT", "MS"):
        pts, label = 100, "Centro-Oeste — cerrado produtivo"
    elif s in ("TO", "MA", "PI", "BA"):
        pts, label = 80, "MATOPIBA — expansão com riscos hídricos"
    else:
        pts, label = 60, "Nordeste/Norte — alta variabilidade climática"
    return pts, label


def _score_maturidade(years: int) -> tuple:
    """Dimensão 4 — Maturidade operacional (0-150)."""
    if years > 20:
        pts, label = 150, "Veterano (>20 anos)"
    elif years >= 10:
        pts, label = 120, "Experiente (10-20 anos)"
    elif years >= 5:
        pts, label = 90, "Consolidado (5-10 anos)"
    elif years >= 2:
        pts, label = 60, "Emergente (2-5 anos)"
    else:
        pts, label = 30, "Iniciante (<2 anos)"
    return pts, label


def _score_certs(certs: list) -> tuple:
    """Dimensão 5 — Certificações (0-100)."""
    n = len(certs) if certs else 0
    has_organic = any("orgân" in str(c).lower() or "organic" in str(c).lower() for c in (certs or []))
    has_global = any("global" in str(c).lower() for c in (certs or []))
    has_rastreav = any("rastreáv" in str(c).lower() or "rastreav" in str(c).lower() for c in (certs or []))
    if has_organic and has_global and has_rastreav:
        pts, label = 100, "Orgânico + GlobalGAP + Rastreável"
    elif n >= 2:
        pts, label = 70, f"{n} certificações"
    elif n == 1:
        pts, label = 40, "1 certificação"
    else:
        pts, label = 10, "Sem certificações"
    return pts, label


def _score_judicial(producer_name: str) -> tuple:
    """Dimensão 6 — Histórico judicial (busca DB, 0 a -200)."""
    penalty, label = 0, "Sem processos encontrados"
    try:
        conn = get_conn()
        name_q = f"%{producer_name}%" if producer_name else "%"
        # Tabelas possíveis: judicial_records, litigation, processos
        tables_to_try = [
            ("judicial_records", "defendant_name", "case_type"),
            ("litigation", "name", "type"),
            ("processos", "nome", "tipo"),
        ]
        for tbl, name_col, type_col in tables_to_try:
            try:
                rows = conn.execute(
                    f"SELECT {type_col} FROM {tbl} WHERE {name_col} LIKE ? LIMIT 10",
                    (name_q,)
                ).fetchall()
                if rows:
                    types_found = [r[0] for r in rows]
                    severe = any(
                        any(k in str(t).lower() for k in ["falência", "falencia", "recuperação", "recuperacao", "bankruptcy"])
                        for t in types_found
                    )
                    if severe:
                        penalty, label = -200, "Falência / recuperação judicial detectada"
                    elif len(rows) >= 3:
                        penalty, label = -100, f"{len(rows)} processos no histórico"
                    else:
                        penalty, label = -50, f"{len(rows)} processo(s) menores"
                    break
            except Exception:
                continue
    except Exception:
        pass
    return penalty, label


def _score_diversificacao(culture: str) -> tuple:
    """Dimensão 7 — Diversificação (inferida por campo livre, 0-50)."""
    # Heurística: conta culturas mencionadas na string de cultura
    cultures_keywords = [
        "soja", "milho", "tomate", "café", "cafe", "cebola", "alho", "feijão",
        "feijao", "arroz", "trigo", "mandioca", "laranja", "banana", "uva",
        "sorgo", "algodão", "algodao", "girassol", "amendoim"
    ]
    c = (culture or "").lower()
    found = sum(1 for k in cultures_keywords if k in c)
    if found >= 3:
        pts, label = 50, "Alta diversificação (3+ culturas)"
    elif found == 2:
        pts, label = 30, "Diversificação moderada (2 culturas)"
    else:
        pts, label = 0, "Monocultura"
    return pts, label


def _score_credito(data: dict) -> tuple:
    """Dimensão 8 — Acesso a crédito/seguro (0-100)."""
    # Inferido de campos opcionais no body
    has_credit = data.get("has_credit", False) or data.get("pronaf", False) or data.get("pronamp", False)
    has_insurance = data.get("has_insurance", False) or data.get("seguro_safra", False)
    if has_credit and has_insurance:
        pts, label = 100, "Pronaf/Pronamp + Seguro Safra"
    elif has_credit:
        pts, label = 60, "Apenas crédito rural"
    elif has_insurance:
        pts, label = 40, "Apenas seguro agrícola"
    else:
        pts, label = 0, "Sem crédito nem seguro"
    return pts, label


def _build_recommendations(dims: dict) -> list:
    recs = []
    if dims["escala"]["pts"] < 130:
        recs.append("Expandir área cultivada ou formar consórcio com produtores vizinhos para ganho de escala.")
    if dims["certs"]["pts"] < 70:
        recs.append("Obter certificação orgânica e GlobalGAP pode adicionar até +60 pontos de score.")
    if dims["maturidade"]["pts"] < 90:
        recs.append("Registrar histórico operacional documentado fortalece a maturidade percebida.")
    if dims["judicial"]["pts"] < 0:
        recs.append("Regularizar pendências judiciais é prioridade — impacto severo no score.")
    if dims["credito"]["pts"] < 60:
        recs.append("Aderir ao Pronaf/Pronamp e contratar Seguro Safra aumenta acesso a financiamentos.")
    if dims["diversificacao"]["pts"] < 30:
        recs.append("Diversificar culturas reduz risco climático e pode ampliar pontuação em +50.")
    return recs


def _compute_score(data: dict) -> dict:
    area_ha = float(data.get("area_ha", 0) or 0)
    culture = str(data.get("culture", "") or "")
    state = str(data.get("state", "") or "")
    years = int(data.get("years_operating", 0) or 0)
    certs = data.get("certifications", []) or []
    name = str(data.get("name", "") or "")

    e_pts, e_lbl = _score_escala(area_ha)
    c_pts, c_lbl = _score_cultura(culture)
    z_pts, z_lbl = _score_zona(state)
    m_pts, m_lbl = _score_maturidade(years)
    cert_pts, cert_lbl = _score_certs(certs)
    j_pts, j_lbl = _score_judicial(name)
    d_pts, d_lbl = _score_diversificacao(culture)
    cr_pts, cr_lbl = _score_credito(data)

    dims = {
        "escala":         {"pts": e_pts,    "max": 200, "label": e_lbl},
        "cultura":        {"pts": c_pts,    "max": 150, "label": c_lbl},
        "zona":           {"pts": z_pts,    "max": 150, "label": z_lbl},
        "maturidade":     {"pts": m_pts,    "max": 150, "label": m_lbl},
        "certs":          {"pts": cert_pts, "max": 100, "label": cert_lbl},
        "judicial":       {"pts": j_pts,    "max": 0,   "label": j_lbl},
        "diversificacao": {"pts": d_pts,    "max": 50,  "label": d_lbl},
        "credito":        {"pts": cr_pts,   "max": 100, "label": cr_lbl},
    }

    total = sum(v["pts"] for v in dims.values())
    total = max(0, min(1000, total))  # clamp 0-1000

    if total >= 800:
        rating = "AAA"
    elif total >= 650:
        rating = "AA"
    elif total >= 500:
        rating = "A"
    elif total >= 350:
        rating = "BBB"
    elif total >= 200:
        rating = "BB"
    else:
        rating = "B"

    return {
        "producer_name": name or "N/A",
        "state": state,
        "culture": culture,
        "area_ha": area_ha,
        "score": total,
        "rating": rating,
        "max_possible": 900,
        "dimensions": dims,
        "recommendations": _build_recommendations(dims),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Handler ──────────────────────────────────────────────────────────────────

def handle_producer_score(handler, path):
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(path)
        qs = parse_qs(parsed.query)

        method = handler.command if hasattr(handler, "command") else "GET"

        if method == "POST":
            length = int(handler.headers.get("Content-Length", 0))
            body = handler.rfile.read(length) if length else b"{}"
            data = json.loads(body or b"{}")
        else:
            # GET com query params mínimos
            data = {
                "state": qs.get("state", [""])[0],
                "culture": qs.get("culture", ["soja"])[0],
                "area_ha": float(qs.get("area_ha", [500])[0]),
                "years_operating": int(qs.get("years", [5])[0]),
                "certifications": [],
                "name": qs.get("name", [""])[0],
            }

        result = _compute_score(data)
        body_out = json.dumps(result, ensure_ascii=False).encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(body_out)

    except Exception as e:
        err = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(err)
