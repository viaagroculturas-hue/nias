"""NIAS — Pré-Venda API: timing e preço ótimo de travamento de safra."""
import json
import os
import time
import urllib.request
from datetime import datetime, timezone

from flv.db import get_conn


# ─── Histórico de preços do DB ────────────────────────────────────────────────

def _fetch_historical_prices(product: str, harvest_month: int) -> list:
    """Busca preços históricos do mesmo produto/mês nos últimos 2 anos."""
    conn = get_conn()
    prices = []
    tables_to_try = [
        ("flv_prices",     "product", "price", "collected_at"),
        ("prices",         "product", "price", "date"),
        ("ceasa_prices",   "product", "price", "date"),
        ("market_prices",  "produto", "preco", "data"),
    ]
    for tbl, p_col, v_col, d_col in tables_to_try:
        try:
            rows = conn.execute(
                f"""
                SELECT {v_col} FROM {tbl}
                WHERE LOWER({p_col}) LIKE ?
                  AND CAST(strftime('%m', {d_col}) AS INTEGER) = ?
                  AND {d_col} >= date('now', '-2 years')
                ORDER BY {d_col} DESC
                LIMIT 200
                """,
                (f"%{product.lower()}%", harvest_month),
            ).fetchall()
            if rows:
                prices = [float(r[0]) for r in rows if r[0] is not None]
                break
        except Exception:
            continue
    return prices


def _historical_avg(prices: list, fallback: float) -> float:
    if not prices:
        return fallback
    return sum(prices) / len(prices)


def _volatility(prices: list) -> float:
    if len(prices) < 2:
        return 0.0
    mean = sum(prices) / len(prices)
    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
    return (variance ** 0.5) / mean if mean else 0.0


# ─── Chamada Claude Haiku ─────────────────────────────────────────────────────

def _ai_justification(product: str, current_price: float, hist_avg: float,
                       pct_vs_hist: float, recommendation: str, lock_pct: int) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "Justificativa IA indisponível — ANTHROPIC_API_KEY não configurada."

    prompt = (
        f"Você é um analista de mercado agrícola NIAS. "
        f"O produto é {product}. Preço atual: R$ {current_price:.2f}/ton. "
        f"Média histórica do mês de colheita: R$ {hist_avg:.2f}/ton ({pct_vs_hist:+.1f}%). "
        f"Recomendação: {recommendation} — travar {lock_pct}% da produção agora. "
        f"Escreva em 2 frases objetivas em português brasileiro explicando por que esta recomendação "
        f"é adequada neste contexto de mercado, citando a relação preço×histórico."
    )

    body = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read())
            return resp_data["content"][0]["text"].strip()
    except Exception as ex:
        return f"Justificativa IA indisponível: {ex}"


# ─── Lógica principal ─────────────────────────────────────────────────────────

def _compute_prevenda(data: dict) -> dict:
    product          = str(data.get("product", "soja"))
    qty              = float(data.get("quantity_tons", 1) or 1)
    harvest_str      = str(data.get("harvest_date_estimate", "") or "")
    state            = str(data.get("state", "") or "")
    current_price    = float(data.get("current_market_price", 0) or 0)

    # Mês de colheita
    harvest_month = 3  # default março
    if harvest_str:
        try:
            dt = datetime.fromisoformat(harvest_str)
            harvest_month = dt.month
        except Exception:
            pass

    # Histórico de preços
    hist_prices = _fetch_historical_prices(product, harvest_month)
    hist_avg    = _historical_avg(hist_prices, current_price)
    vol         = _volatility(hist_prices)

    pct_vs_hist = ((current_price - hist_avg) / hist_avg * 100) if hist_avg else 0.0

    # Recomendação de travamento
    if pct_vs_hist >= 15:
        recommendation = "TRAVAR_70"
        lock_pct       = 70
        lock_label     = "TRAVAR 70% AGORA — preço excepcionalmente acima do histórico"
        lock_window    = "Esta semana"
    elif pct_vs_hist >= 0:
        recommendation = "TRAVAR_50"
        lock_pct       = 50
        lock_label     = "TRAVAR 50% AGORA — preço dentro do range favorável"
        lock_window    = "Próximas 2 semanas"
    elif pct_vs_hist >= -15:
        recommendation = "TRAVAR_30"
        lock_pct       = 30
        lock_label     = "TRAVAR 30% AGORA — preço abaixo, mas hedge parcial é prudente"
        lock_window    = "Próximas 4 semanas"
    else:
        recommendation = "AGUARDAR"
        lock_pct       = 0
        lock_label     = "AGUARDAR — preço significativamente abaixo da média histórica"
        lock_window    = "Reavaliar em 30 dias"

    # Cenários de receita
    spot_estimate = current_price * (1 + 0.05)  # estimativa spot +5% ao colher
    scenarios = []
    for pct in [30, 50, 70]:
        locked_qty   = qty * pct / 100
        spot_qty     = qty * (1 - pct / 100)
        locked_rev   = locked_qty * current_price
        spot_rev     = spot_qty * spot_estimate
        total_est    = locked_rev + spot_rev
        scenarios.append({
            "lock_pct":             pct,
            "locked_revenue_brl":   round(locked_rev, 2),
            "spot_revenue_estimate": round(spot_rev, 2),
            "total_estimate":       round(total_est, 2),
        })

    # Fatores de risco
    risk_factors = []
    if vol > 0.15:
        risk_factors.append(f"Alta volatilidade histórica ({vol*100:.1f}%) — janela de travamento mais urgente.")
    if pct_vs_hist < -10:
        risk_factors.append("Preço corrente abaixo do histórico — risco de queda adicional se aguardar.")
    if state.upper() in ("MT", "MS", "GO", "TO", "BA", "MA", "PI"):
        risk_factors.append("Região MATOPIBA/Cerrado sujeita a variabilidade hídrica — considere El Niño/La Niña.")
    # ONI simplificado — mês de maio-agosto = La Niña recomenda mais cautela
    now_month = datetime.now().month
    if now_month in range(5, 9):
        risk_factors.append("Janela climática austral (mai-ago): monitorar ONI. El Niño ativo recomenda travar mais cedo.")

    # Justificativa IA
    ai_just = _ai_justification(product, current_price, hist_avg, pct_vs_hist, recommendation, lock_pct)

    return {
        "product":              product,
        "quantity_tons":        qty,
        "harvest_date":         harvest_str,
        "state":                state,
        "current_price":        round(current_price, 2),
        "historical_avg_price": round(hist_avg, 2),
        "historical_samples":   len(hist_prices),
        "pct_vs_historical":    round(pct_vs_hist, 2),
        "volatility_pct":       round(vol * 100, 2),
        "recommendation":       recommendation,
        "recommendation_label": lock_label,
        "pct_to_lock":          lock_pct,
        "optimal_lock_window":  lock_window,
        "scenarios":            scenarios,
        "risk_factors":         risk_factors,
        "ai_justification":     ai_just,
        "generated_at":         datetime.now(timezone.utc).isoformat(),
    }


# ─── Handler ──────────────────────────────────────────────────────────────────

def handle_pre_venda(handler, path):
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body   = handler.rfile.read(length) if length else b"{}"
        data   = json.loads(body or b"{}")
        result = _compute_prevenda(data)
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
