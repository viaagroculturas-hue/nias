"""Cliente CNJ DataJud para Recuperação Judicial/Falência.

Uso seguro:
- Não simula empresas.
- Sem DATAJUD_API_KEY, retorna status de configuração.
- Com chave, consulta aliases dos tribunais e devolve metadados públicos.
"""
from __future__ import annotations

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

DATAJUD_BASE_URL = os.environ.get("DATAJUD_BASE_URL", "https://api-publica.datajud.cnj.jus.br")
DATAJUD_API_KEY = os.environ.get("DATAJUD_API_KEY", "").strip()

# Tribunais estaduais mais relevantes para agro e abastecimento. Pode ser expandido.
DEFAULT_TRIBUNALS = [
    "tjsp", "tjmg", "tjgo", "tjmt", "tjms", "tjpr", "tjrs", "tjsc", "tjba", "tjpe", "tjrj", "tjes",
    "tjma", "tjpa", "tjto", "tjro", "tjpi", "tjce", "tjrn", "tjpb", "tjal", "tjse", "tjdf"
]

# CNJ DataJud usa metadados de processos. A filtragem exata depende do tribunal/índice.
RECOVERY_TERMS = [
    "recuperação judicial",
    "recuperacao judicial",
    "falência",
    "falencia",
    "recuperação extrajudicial",
    "recuperacao extrajudicial",
]


def _headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if DATAJUD_API_KEY:
        headers["Authorization"] = f"APIKey {DATAJUD_API_KEY}"
    return headers


def _post_json(url: str, payload: Dict[str, Any], timeout: int = 25) -> Dict[str, Any]:
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=_headers(), method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def build_recovery_query(size: int = 50, search_after: Optional[List[Any]] = None, uf_hint: Optional[str] = None) -> Dict[str, Any]:
    should_terms = [{"match_phrase": {"classe.nome": term}} for term in RECOVERY_TERMS]
    should_terms += [{"match_phrase": {"assuntos.nome": term}} for term in RECOVERY_TERMS]
    should_terms += [{"match_phrase": {"movimentos.nome": term}} for term in RECOVERY_TERMS]
    must = [{"bool": {"should": should_terms, "minimum_should_match": 1}}]
    if uf_hint:
        must.append({"match": {"tribunal": uf_hint.upper()}})
    query: Dict[str, Any] = {
        "size": size,
        "query": {"bool": {"must": must}},
        "sort": [{"dataHoraUltimaAtualizacao": {"order": "desc"}}, {"@timestamp": {"order": "desc"}}],
    }
    if search_after:
        query["search_after"] = search_after
    return query


def query_tribunal(alias: str, size: int = 50) -> Dict[str, Any]:
    if not DATAJUD_API_KEY:
        return {
            "status": "configuration_needed",
            "alias": alias,
            "message": "Configure DATAJUD_API_KEY no Render para consulta oficial em tempo real.",
            "records": [],
        }
    url = f"{DATAJUD_BASE_URL.rstrip('/')}/api_publica_{alias}/_search"
    try:
        data = _post_json(url, build_recovery_query(size=size))
        hits = data.get("hits", {}).get("hits", [])
        return {"status": "ok", "alias": alias, "records": [h.get("_source", {}) for h in hits], "raw_total": data.get("hits", {}).get("total")}
    except urllib.error.HTTPError as e:
        return {"status": "error", "alias": alias, "error": f"HTTP {e.code}", "records": []}
    except Exception as e:
        return {"status": "error", "alias": alias, "error": str(e), "records": []}


def query_recovery_judicial(tribunals: Optional[List[str]] = None, size_per_tribunal: int = 25) -> Dict[str, Any]:
    tribunals = tribunals or DEFAULT_TRIBUNALS
    results = []
    status_count: Dict[str, int] = {}
    for alias in tribunals:
        r = query_tribunal(alias, size=size_per_tribunal)
        status_count[r["status"]] = status_count.get(r["status"], 0) + 1
        results.append(r)
    return {
        "status": "ok" if status_count.get("ok") else "configuration_needed" if status_count.get("configuration_needed") else "partial_error",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "CNJ DataJud API Pública",
        "tribunals_checked": tribunals,
        "status_count": status_count,
        "results": results,
    }
