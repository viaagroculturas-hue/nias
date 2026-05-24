"""Analisador de informações para a aba IA.

Gera diagnóstico determinístico a partir do SQLite local, sem inventar fontes.
Classifica frescor, qualidade, anomalias e recomendações operacionais.
"""
from __future__ import annotations

from datetime import datetime, date
from statistics import mean
from typing import Any, Dict, List, Optional


def _parse_date(value: Any) -> Optional[date]:
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:19] if "%H" in fmt else s[:10], fmt).date()
        except Exception:
            pass
    # Faixas antigas do tipo "30-06-2025 - 04-07-2025": usa a data final.
    if " - " in s:
        right = s.split(" - ")[-1].strip()
        try:
            return datetime.strptime(right, "%d-%m-%Y").date()
        except Exception:
            return None
    return None


def _days_old(value: Any) -> Optional[int]:
    d = _parse_date(value)
    return (date.today() - d).days if d else None


def _safe_pct(num: float, den: float) -> float:
    return round((num / den * 100), 1) if den else 0.0


def _query(sql: str, params=()):
    from flv.db import query
    return query(sql, params)


def analyze_information() -> Dict[str, Any]:
    """Return IA-ready analysis payload for the dashboard."""
    generated_at = datetime.now().isoformat(timespec="seconds")
    cards: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []
    recommendations: List[str] = []

    def add_finding(level: str, title: str, detail: str, metric: Optional[str] = None):
        findings.append({"level": level, "title": title, "detail": detail, "metric": metric})

    # Totais e qualidade por tabela crítica.
    table_quality = []
    for table, date_col in [
        ("flv_ceasa_prices", "price_date"),
        ("flv_ndvi", "obs_date"),
        ("flv_climate", "obs_date"),
        ("flv_news_events", "obs_ts"),
        ("flv_macro_indicators", "obs_date"),
    ]:
        rows = _query(f"""
            SELECT COUNT(*) AS total,
                   SUM(COALESCE(is_synthetic,0)) AS synthetic,
                   MAX({date_col}) AS latest
            FROM {table}
        """)
        r = rows[0] if rows else {"total": 0, "synthetic": 0, "latest": None}
        total = int(r.get("total") or 0)
        synthetic = int(r.get("synthetic") or 0)
        latest = r.get("latest")
        table_quality.append({
            "table": table,
            "total": total,
            "synthetic": synthetic,
            "synthetic_pct": _safe_pct(synthetic, total),
            "latest": latest,
            "days_old": _days_old(latest),
        })

    total_rows = sum(t["total"] for t in table_quality)
    total_synth = sum(t["synthetic"] for t in table_quality)
    latest_dates = [t["days_old"] for t in table_quality if t["days_old"] is not None]
    freshness = min(latest_dates) if latest_dates else None

    cards.append({"label": "Registros analisados", "value": f"{total_rows:,}".replace(",", "."), "status": "ok" if total_rows else "danger"})
    cards.append({"label": "Sintéticos/proxy", "value": f"{_safe_pct(total_synth, total_rows)}%", "status": "warn" if total_synth else "ok"})
    cards.append({"label": "Frescor mínimo", "value": f"D-{freshness}" if freshness is not None else "sem data", "status": "ok" if freshness is not None and freshness <= 7 else "warn"})

    # Preços: últimas cotações por cultura e variação simples.
    prices = _query("""
        SELECT c.slug, c.name_pt, p.terminal, p.price_date, p.price_avg,
               COALESCE(p.is_synthetic,0) AS is_synthetic, COALESCE(p.data_quality,'') AS data_quality
        FROM flv_ceasa_prices p
        JOIN flv_cultures c ON c.id = p.culture_id
        WHERE p.price_avg IS NOT NULL
        ORDER BY date(p.price_date) DESC, p.id DESC
        LIMIT 200
    """)
    latest_by_slug: Dict[str, Dict[str, Any]] = {}
    for p in prices:
        latest_by_slug.setdefault(p["slug"], p)

    top_prices = []
    for slug, p in list(latest_by_slug.items())[:12]:
        hist = _query("""
            SELECT price_avg FROM flv_ceasa_prices p
            JOIN flv_cultures c ON c.id=p.culture_id
            WHERE c.slug=? AND p.price_avg IS NOT NULL
            ORDER BY date(p.price_date) DESC, p.id DESC LIMIT 8
        """, (slug,))
        vals = [float(x["price_avg"]) for x in hist if x.get("price_avg") is not None]
        avg_prev = mean(vals[1:]) if len(vals) > 1 else vals[0] if vals else None
        change = ((vals[0] - avg_prev) / avg_prev * 100) if avg_prev else 0
        top_prices.append({
            "culture": p["name_pt"],
            "terminal": p["terminal"],
            "date": p["price_date"],
            "price": round(float(p["price_avg"]), 2),
            "change_pct": round(change, 1),
            "synthetic": bool(p["is_synthetic"]),
        })

    movers = sorted(top_prices, key=lambda x: abs(x["change_pct"]), reverse=True)[:5]
    if movers:
        add_finding(
            "info",
            "Maiores movimentos de preço detectados",
            "; ".join([f"{m['culture']}: {m['change_pct']}%" for m in movers]),
            f"{len(movers)} culturas"
        )

    # Alertas vigentes.
    alerts = _query("""
        SELECT a.alert_type, a.severity, a.message, a.impact_price_pct, a.valid_until,
               c.name_pt AS culture_name, m.name AS municipality, m.state_uf
        FROM flv_alerts a
        LEFT JOIN flv_cultures c ON c.id=a.culture_id
        LEFT JOIN flv_municipalities m ON m.id=a.mun_id
        WHERE a.valid_until IS NULL OR datetime(a.valid_until) > datetime('now')
        ORDER BY CASE a.severity WHEN 'vermelho' THEN 0 WHEN 'laranja' THEN 1 ELSE 2 END,
                 ABS(COALESCE(a.impact_price_pct,0)) DESC
        LIMIT 10
    """)
    red_alerts = [a for a in alerts if a.get("severity") == "vermelho"]
    cards.append({"label": "Alertas vigentes", "value": str(len(alerts)), "status": "danger" if red_alerts else "warn" if alerts else "ok"})
    if red_alerts:
        add_finding("danger", "Alertas vermelhos ativos", f"{len(red_alerts)} evento(s) crítico(s) em cultura/região monitorada.", str(len(red_alerts)))
        recommendations.append("Priorizar validação manual dos alertas vermelhos antes de decisão comercial ou logística.")

    # NDVI: anomalias e origem proxy/sintética.
    ndvi_summary = _query("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN COALESCE(is_synthetic,0)=1 OR lower(COALESCE(source,'')) LIKE '%synthetic%' THEN 1 ELSE 0 END) AS synthetic,
               AVG(ndvi_value) AS avg_ndvi,
               MIN(ndvi_value) AS min_ndvi,
               MAX(obs_date) AS latest
        FROM flv_ndvi
    """)[0]
    ndvi_total = int(ndvi_summary.get("total") or 0)
    ndvi_synth = int(ndvi_summary.get("synthetic") or 0)
    if ndvi_total and _safe_pct(ndvi_synth, ndvi_total) >= 50:
        add_finding("warn", "NDVI majoritariamente sintético/proxy", "A camada deve ser usada como sinal auxiliar, não como observação orbital oficial.", f"{_safe_pct(ndvi_synth, ndvi_total)}%")
        recommendations.append("Rotular visualmente NDVI proxy na interface e impedir que ele gere alertas críticos sozinho.")

    # Macroeconomia: campos nulos e faixas inválidas.
    macro = _query("""
        SELECT obs_date, diesel_brl_l, usd_brl, selic_pct, ipca_yoy_pct, source,
               COALESCE(is_synthetic,0) AS is_synthetic
        FROM flv_macro_indicators ORDER BY date(obs_date) DESC LIMIT 1
    """)
    if macro:
        m = macro[0]
        missing = [k for k in ("diesel_brl_l", "usd_brl", "selic_pct", "ipca_yoy_pct") if m.get(k) is None]
        if missing:
            add_finding("warn", "Indicadores macroeconômicos incompletos", "Campos ausentes: " + ", ".join(missing), m.get("obs_date"))
        ipca = m.get("ipca_yoy_pct")
        if ipca is not None and not (-10 <= float(ipca) <= 30):
            add_finding("danger", "IPCA fora de faixa plausível", f"Valor gravado: {ipca}% a.a.", "validar fonte")
            recommendations.append("Reexecutar coleta macro e descartar leituras fora de faixa antes de alimentar previsões.")

    # Previsões: target no passado em relação ao generated_at.
    pred_issue = _query("""
        SELECT COUNT(*) AS total,
               SUM(CASE WHEN date(target_date) < date(generated_at) THEN 1 ELSE 0 END) AS past_targets,
               MAX(generated_at) AS latest_generated
        FROM flv_predictions
    """)[0]
    pred_total = int(pred_issue.get("total") or 0)
    past_targets = int(pred_issue.get("past_targets") or 0)
    if pred_total and past_targets:
        add_finding("danger", "Previsões com data-alvo no passado", "Há previsões que não representam horizonte futuro válido.", f"{past_targets}/{pred_total}")
        recommendations.append("Regerar previsões após normalizar datas ISO e ordenar séries por date(price_date).")

    # Pontuação simples de confiabilidade.
    penalty = 0
    penalty += min(35, int(_safe_pct(total_synth, total_rows) * 0.35))
    penalty += 20 if any(f["level"] == "danger" for f in findings) else 0
    penalty += 10 if freshness is None or freshness > 14 else 0
    confidence = max(0, min(100, 92 - penalty))
    cards.append({"label": "Confiabilidade IA", "value": f"{confidence}%", "status": "ok" if confidence >= 75 else "warn" if confidence >= 55 else "danger"})

    if not recommendations:
        recommendations.append("Manter rotina de coleta e auditoria; nenhuma anomalia crítica foi detectada no ciclo atual.")

    summary = (
        f"Análise executada sobre {total_rows} registros. "
        f"Confiabilidade operacional estimada em {confidence}%. "
        f"Foram encontrados {len([f for f in findings if f['level']=='danger'])} achado(s) crítico(s) "
        f"e {len([f for f in findings if f['level']=='warn'])} ponto(s) de atenção."
    )

    return {
        "generated_at": generated_at,
        "summary": summary,
        "confidence_pct": confidence,
        "cards": cards,
        "findings": findings,
        "recommendations": recommendations[:8],
        "prices": top_prices,
        "alerts": alerts,
        "quality": table_quality,
    }
