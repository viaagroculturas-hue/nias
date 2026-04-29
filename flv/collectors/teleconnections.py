"""
Teleconexões — clima global que impacta safra local.

Implementação inicial: valores "best-effort" via endpoints públicos (quando disponíveis).
Se falhar, mantém último valor gravado (via regressors persistentes).
"""

from __future__ import annotations

import csv
import io
import json
import re
import urllib.request
from datetime import datetime


def _fetch_json(url: str, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _fetch_text(url: str, timeout=20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def _latest_oni_from_noaa() -> float | None:
    """
    Lê a tabela oficial ONI da NOAA/CPC.

    O endpoint é texto fixo; a função tolera mudanças pequenas de espaçamento e
    retorna o último valor numérico disponível.
    """
    text = _fetch_text("https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt", timeout=15)
    vals: list[float] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or not any(p.isdigit() and len(p) == 4 for p in parts):
            continue
        try:
            vals.append(float(parts[-1]))
        except Exception:
            continue
    return vals[-1] if vals else None


def _latest_atlantic_sst_anomaly() -> float | None:
    """
    Proxy de aquecimento do Atlântico Norte via ERSST NCDC.

    Usa o índice Nino/teleconexão como série mensal de anomalia de SST no
    Atlântico Norte quando o formato CSV está disponível publicamente.
    """
    urls = [
        "https://www.ncei.noaa.gov/access/monitoring/teleconnections/nao/data.csv",
        "https://www.ncei.noaa.gov/access/monitoring/teleconnections/amo/data.csv",
    ]
    for url in urls:
        try:
            text = _fetch_text(url, timeout=15)
            rows = csv.reader(io.StringIO(text))
            vals: list[float] = []
            for row in rows:
                if len(row) < 2:
                    continue
                joined = ",".join(row)
                nums = re.findall(r"-?\d+(?:\.\d+)?", joined)
                if nums:
                    try:
                        vals.append(float(nums[-1]))
                    except Exception:
                        pass
            if vals:
                return vals[-1]
        except Exception:
            continue
    return None


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
    sources = []

    try:
        oni = _latest_oni_from_noaa()
        sources.append("NOAA/CPC ONI")
    except Exception:
        pass

    try:
        atl = _latest_atlantic_sst_anomaly()
        if atl is not None:
            sources.append("NOAA/NCEI Atlantic")
    except Exception:
        pass

    if oni is None and atl is None:
        # Mantem compatibilidade com o comportamento anterior: falhas de rede nao
        # derrubam a pipeline e o modelo persiste o ultimo regressor conhecido.
        source = "NOAA(best-effort)"
    else:
        source = "/".join(sources) if sources else "NOAA(best-effort)"

    upsert_global_climate(obs_date=obs_date, oni=oni, atl_north_warm_idx=atl, source=source)
    print(f"[FLV-Teleconnections] {obs_date} oni={oni} atl_north_warm_idx={atl}")
    return {"obs_date": obs_date, "oni": oni, "atl_north_warm_idx": atl}

