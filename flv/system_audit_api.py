"""System audit and trusted-source API for NIA/FLV.

Purpose:
- expose a transparent inventory of official sources;
- identify local synthetic/proxy data without presenting it as real;
- provide a consolidated health payload for the UI.
"""
from __future__ import annotations
import json, os, sqlite3, time
from datetime import datetime, timezone
from typing import Any

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(os.path.dirname(__file__), "trusted_source_registry.json")
DB_CANDIDATES = [os.path.join(ROOT, "nia_flv.db"), os.path.join(ROOT, "flv", "nia_flv.db")]

CORE_TABS = [
    {"id":"overview", "label":"Visão Geral", "status":"keep", "reason":"painel executivo"},
    {"id":"municipal", "label":"Municipal", "status":"keep", "reason":"produção/localização"},
    {"id":"biocommand", "label":"Bio-Command", "status":"keep", "reason":"risco bioclimático"},
    {"id":"oferta", "label":"Mercado", "status":"keep", "reason":"preços e oferta"},
    {"id":"situation", "label":"Situation", "status":"keep", "reason":"riscos, RJ e impacto setorial"},
    {"id":"chat", "label":"IA", "status":"keep", "reason":"análise consolidada"},
]
DEPRECATED_TABS = [
    {"id":"map", "label":"Mapa legado", "status":"hidden", "reason":"duplicado com Municipal/Bio-Command"},
    {"id":"logistica", "label":"Logística legado", "status":"hidden", "reason":"consolidado em Situation"},
    {"id":"warroom", "label":"War Room", "status":"hidden", "reason":"alertas consolidados em Situation"},
    {"id":"flv_insights", "label":"FLV legado", "status":"hidden", "reason":"previsões consolidadas em IA/Situation"},
    {"id":"flv_reports", "label":"Relatórios FLV legado", "status":"hidden", "reason":"redundante"},
    {"id":"predictix", "label":"PredictX/Predictix", "status":"hidden", "reason":"consolidado em Situation + IA"},
    {"id":"macropolos", "label":"Macropolos", "status":"hidden", "reason":"duplicado com Municipal"},
    {"id":"hyperlocal", "label":"Hyperlocal", "status":"hidden", "reason":"sem fonte operacional configurada"},
    {"id":"sentiment", "label":"Sentimento", "status":"hidden", "reason":"sem fonte pública auditável configurada"},
    {"id":"esg", "label":"ESG", "status":"hidden", "reason":"sem base oficial dinâmica integrada"},
]

def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def _load_registry() -> dict[str, Any]:
    with open(REGISTRY, "r", encoding="utf-8") as f:
        return json.load(f)

def _db_path() -> str | None:
    for p in DB_CANDIDATES:
        if os.path.exists(p): return p
    return None

def _query(conn: sqlite3.Connection, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    cur = conn.execute(sql, args)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]

def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return bool(_query(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)))

def data_quality_snapshot() -> dict[str, Any]:
    path = _db_path()
    out = {"database": path, "tables": [], "warnings": []}
    if not path:
        out["warnings"].append("Banco nia_flv.db não encontrado.")
        return out
    conn = sqlite3.connect(path)
    try:
        conn.row_factory = sqlite3.Row
        tables = [r["name"] for r in _query(conn, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for t in tables:
            if not t.startswith("flv_"):
                continue
            cols = [r["name"] for r in _query(conn, f"PRAGMA table_info({t})")]
            row = {"table": t, "rows": _query(conn, f"SELECT COUNT(*) AS n FROM {t}")[0]["n"]}
            if "is_synthetic" in cols:
                q = _query(conn, f"SELECT SUM(COALESCE(is_synthetic,0)) AS synthetic FROM {t}")[0]
                row["synthetic_rows"] = int(q.get("synthetic") or 0)
                if row["synthetic_rows"]:
                    out["warnings"].append(f"{t}: contém {row['synthetic_rows']} linhas sintéticas/proxy.")
            if "data_quality" in cols:
                row["quality"] = _query(conn, f"SELECT COALESCE(data_quality,'unknown') AS status, COUNT(*) AS n FROM {t} GROUP BY COALESCE(data_quality,'unknown')")
            if "source" in cols:
                row["sources_top"] = _query(conn, f"SELECT COALESCE(source,'unknown') AS source, COUNT(*) AS n FROM {t} GROUP BY COALESCE(source,'unknown') ORDER BY n DESC LIMIT 8")
            out["tables"].append(row)
    finally:
        conn.close()
    return out

def build_audit_payload() -> dict[str, Any]:
    registry = _load_registry()
    dq = data_quality_snapshot()
    return {
        "status": "ok_with_transparency" if dq.get("warnings") else "ok",
        "updated_at": _now(),
        "source_policy": registry["policy"],
        "core_tabs": CORE_TABS,
        "hidden_redundant_tabs": DEPRECATED_TABS,
        "trusted_sources": registry["sources"],
        "data_quality": dq,
        "rules": [
            "Dado oficial: somente fonte governamental, instituição técnica ou API documentada.",
            "Dado referencial: fonte reconhecida, mas pode exigir validação/licença/assinatura.",
            "Dado fallback/proxy/sintético: nunca entra em painel como fato; aparece apenas como indisponível ou a validar.",
            "Eventos externos — clima, guerras, greves, fertilizantes, portos — entram como alerta com fonte, data e confiança."
        ]
    }

def build_sources_payload() -> dict[str, Any]:
    r = _load_registry()
    return {"updated_at": _now(), "policy": r["policy"], "sources": r["sources"]}
