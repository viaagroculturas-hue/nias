"""
Teleconexões — clima global que impacta safra local.

Implementação inicial: valores "best-effort" via endpoints públicos (quando disponíveis).
Se falhar, mantém último valor gravado (via regressors persistentes).
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime


def _fetch_json(url: str, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def coletar_teleconexoes_globais():
    """
    Coleta ONI (proxy) e um índice simples de Atlântico Norte (placeholder).

    A allowlist atual nao inclui a fonte oficial de teleconexoes. Para manter a
    ingestao exclusiva, o coletor nao grava novos dados ate haver endpoint
    aprovado entre Reuters, Bloomberg, BBC, Al Jazeera, IBGE ou Banco Central.
    """
    from flv.db import init_db, upsert_global_climate

    try:
        init_db()
    except Exception:
        pass

    obs_date = datetime.now().strftime("%Y-%m-%d")
    print(f"[FLV-Teleconnections] {obs_date} sem ingestao: fonte nao aprovada na governanca")
    return {"obs_date": obs_date, "oni": None, "atl_north_warm_idx": None, "skipped": "fonte_nao_aprovada"}

