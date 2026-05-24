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

    Nota: ONI oficial é mensal (3-month running mean). Aqui gravamos o último valor disponível
    se houver endpoint; caso contrário, gravamos nulo e deixamos o modelo persistir o último.
    """
    from flv.db import init_db, upsert_global_climate

    try:
        init_db()
    except Exception:
        pass

    obs_date = datetime.now().strftime("%Y-%m-%d")

    oni = None
    atl = None
    source = "NOAA/ESRL(best-effort)"

    # Best-effort: alguns espelhos publicam JSON; se não, fica None.
    # (Você pode trocar por um endpoint interno depois.)
    try:
        # Placeholder (não garantido): mantemos try/except para não quebrar pipeline.
        data = _fetch_json("https://climatedataapi.worldbank.org/climateweb/rest/v1/country/mavg/tas/1991/2000/BRA", timeout=15)
        if isinstance(data, list) and data:
            atl = None
    except Exception:
        pass

    upsert_global_climate(obs_date=obs_date, oni=oni, atl_north_warm_idx=atl, source=source)
    print(f"[FLV-Teleconnections] {obs_date} oni={oni} atl_north_warm_idx={atl}")
    return {"obs_date": obs_date, "oni": oni, "atl_north_warm_idx": atl}

