"""Registro factual para Situation Room: Recuperação Judicial.

Combina base pública curada com consulta live ao CNJ/DataJud quando configurada.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from flv.services.datajud_client import query_recovery_judicial

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CURATED_PATH = os.path.join(ROOT, "data", "situation_room", "recovery_judicial_cases.json")


def load_curated_cases() -> List[Dict[str, Any]]:
    try:
        with open(CURATED_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload.get("cases", [])
    except Exception:
        return []


def normalize_case(c: Dict[str, Any]) -> Dict[str, Any]:
    debts = c.get("debts_total")
    employees = c.get("employees")
    score = c.get("risk_score") or 50
    if debts and debts >= 1_000_000_000:
        score = max(score, 85)
    elif debts and debts >= 100_000_000:
        score = max(score, 70)
    return {
        "company_name": c.get("company_name") or c.get("nome") or "Empresa não identificada",
        "cnpj": c.get("cnpj"),
        "process_number": c.get("process_number") or c.get("numeroProcesso"),
        "court": c.get("court") or c.get("tribunal"),
        "judicial_status": c.get("judicial_status", "em_monitoramento"),
        "entry_date": c.get("entry_date"),
        "last_judicial_update": c.get("last_judicial_update") or c.get("dataHoraUltimaAtualizacao"),
        "city": c.get("city"),
        "state_uf": c.get("state_uf"),
        "lat": c.get("lat"),
        "lon": c.get("lon"),
        "segment": c.get("segment", "não classificado"),
        "products": c.get("products", []),
        "affected_sectors": c.get("affected_sectors", []),
        "debts_total": debts,
        "employees": employees,
        "annual_revenue": c.get("annual_revenue"),
        "risk_score": min(int(score), 100),
        "impact_level": c.get("impact_level") or ("alto" if score >= 75 else "médio" if score >= 45 else "baixo"),
        "brazil_impact": c.get("brazil_impact"),
        "regional_channels": c.get("regional_channels", []),
        "source_urls": c.get("source_urls", []),
        "data_confidence": c.get("data_confidence", "base curada; validar no tribunal/DataJud"),
        "source_type": c.get("source_type", "curated_public_source"),
    }


def aggregate(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_uf: Dict[str, int] = {}
    sectors: Dict[str, int] = {}
    entries = 0
    total_debt = 0.0
    for c in cases:
        uf = c.get("state_uf") or "ND"
        by_uf[uf] = by_uf.get(uf, 0) + 1
        if "pedido" in str(c.get("judicial_status", "")).lower() or c.get("entry_date"):
            entries += 1
        if c.get("debts_total"):
            total_debt += float(c["debts_total"])
        for s in c.get("affected_sectors", []):
            sectors[s] = sectors.get(s, 0) + 1
    return {
        "total_cases_loaded": len(cases),
        "entries_with_entry_date": entries,
        "states_covered": len(by_uf),
        "total_debt_brl_known": round(total_debt, 2),
        "by_uf": sorted([{"uf": k, "cases": v} for k, v in by_uf.items()], key=lambda x: x["cases"], reverse=True),
        "top_sectors": sorted([{"sector": k, "cases": v} for k, v in sectors.items()], key=lambda x: x["cases"], reverse=True)[:20],
    }


def build_situation_room_payload(uf: Optional[str] = None, include_live: bool = True, limit: int = 500) -> Dict[str, Any]:
    cases = [normalize_case(c) for c in load_curated_cases()]
    if uf:
        cases = [c for c in cases if str(c.get("state_uf", "")).upper() == uf.upper()]
    cases = cases[:limit]

    live = None
    if include_live:
        live = query_recovery_judicial(size_per_tribunal=10)

    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "panel": "Situation Room — Recuperação Judicial",
        "truth_policy": {
            "exhaustive_mode": "Somente com DATAJUD_API_KEY ativo. Sem isso, o painel exibe base pública curada e informa limitação.",
            "no_fake_data": True,
            "legal_warning": "Use para monitoramento; confirme decisões jurídicas/financeiras no processo e administrador judicial."
        },
        "summary": aggregate(cases),
        "cases": cases,
        "live_datajud": live,
        "sources": [
            {"name": "CNJ DataJud API Pública", "url": "https://datajud-wiki.cnj.jus.br/api-publica/", "type": "oficial"},
            {"name": "AgroGalaxy RI — Recuperação Judicial", "url": "https://ri.agrogalaxy.com.br/recuperacao-judicial/", "type": "empresa/listagem documental"},
            {"name": "EcoAgro — Relatórios processuais Grupo Patense", "url": "https://ecoagro.agr.br/", "type": "securitizadora/relatórios"}
        ]
    }
