"""
Coletor macroeconômico — Indicadores que afetam custos e demanda.

Objetivo: fornecer regressors diários ao modelo (ex.: diesel, USD/BRL, SELIC, IPCA).
"""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime

from flv.governance import require_elite_source


def _bcb_sgs_latest(serie_code: int) -> tuple[str | None, float | None]:
    """
    Retorna (data_yyyy_mm_dd, valor) do último ponto disponível para uma série SGS do BCB.
    """
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie_code}/dados?formato=json"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        return None, None
    if not data:
        return None, None
    last = data[-1]
    # SGS usa dd/mm/yyyy
    dt = last.get("data", "").strip()
    val = last.get("valor", "").strip()
    if not dt or not val:
        return None, None
    try:
        obs = datetime.strptime(dt, "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        obs = None
    try:
        v = float(val.replace(".", "").replace(",", "."))
    except Exception:
        v = None
    return obs, v


def _safe_float(x):
    try:
        return float(x)
    except Exception:
        return None


def _pct_change(curr: float | None, prev: float | None) -> float | None:
    try:
        if curr is None or prev is None or prev == 0:
            return None
        return float((curr - prev) / prev * 100.0)
    except Exception:
        return None


def coletar_indicadores_macro():
    """
    Coleta indicadores macro e grava em `flv_macro_indicators`.

    A salvaguarda de fontes permite apenas Banco Central para indicadores macro.
    Métricas de energia sem endpoint aprovado permanecem nulas.
    """
    from flv.db import init_db, upsert_macro_indicators, query

    # garante schema
    try:
        init_db()
    except Exception:
        pass

    # Séries SGS (códigos conhecidos)
    # 1: USD/BRL (venda) — série clássica
    # 11: SELIC meta a.a. (% a.a.)
    # 433: IPCA (variação mensal, %) -> aqui usamos proxy do último valor mensal
    usd_date, usd = _bcb_sgs_latest(1)
    selic_date, selic = _bcb_sgs_latest(11)
    ipca_date, ipca_mom = _bcb_sgs_latest(433)

    # Normaliza data de gravação: usa a mais recente disponível
    dates = [d for d in [usd_date, selic_date, ipca_date] if d]
    obs_date = max(dates) if dates else datetime.now().strftime("%Y-%m-%d")

    # Diesel/energia: sem fonte aprovada na allowlist atual, mantemos nulo.
    diesel_brl_l = None
    diesel_change_pct = None
    brent_usd = None
    wti_usd = None

    # Change % diário (vs último ponto gravado)
    last = None
    try:
        rows = query("SELECT brent_usd, wti_usd FROM flv_macro_indicators ORDER BY obs_date DESC LIMIT 1")
        last = rows[0] if rows else None
    except Exception:
        last = None

    brent_change_pct = _pct_change(brent_usd, (last or {}).get("brent_usd"))
    wti_change_pct = _pct_change(wti_usd, (last or {}).get("wti_usd"))

    # IPCA YoY: não é trivial via SGS sem outra série; como fallback, gravamos o último MoM
    ipca_yoy_pct = ipca_mom

    upsert_macro_indicators(
        obs_date=obs_date,
        diesel_brl_l=_safe_float(diesel_brl_l),
        diesel_change_pct=_safe_float(diesel_change_pct),
        brent_usd=_safe_float(brent_usd),
        brent_change_pct=_safe_float(brent_change_pct),
        wti_usd=_safe_float(wti_usd),
        wti_change_pct=_safe_float(wti_change_pct),
        usd_brl=_safe_float(usd),
        selic_pct=_safe_float(selic),
        ipca_yoy_pct=_safe_float(ipca_yoy_pct),
        source=require_elite_source("BCB"),
    )

    print(
        f"[FLV-Macro] {obs_date} salvo: USD={usd} SELIC={selic} IPCA(proxy)={ipca_yoy_pct} "
        f"Brent={brent_usd} WTI={wti_usd} Diesel={diesel_brl_l}"
    )
    return {
        "obs_date": obs_date,
        "usd_brl": usd,
        "selic_pct": selic,
        "ipca_yoy_pct": ipca_yoy_pct,
        "diesel_brl_l": diesel_brl_l,
        "diesel_change_pct": diesel_change_pct,
        "brent_usd": brent_usd,
        "brent_change_pct": brent_change_pct,
        "wti_usd": wti_usd,
        "wti_change_pct": wti_change_pct,
    }

