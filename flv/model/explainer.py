"""
Explainer — relatório inteligente (Gemini) com fallback.

Se `GEMINI_API_KEY` existir e o SDK `google-generativeai` estiver instalado,
o sistema gera um texto contextual via Gemini. Caso falhe (sem chave/quota/erro),
entra automaticamente em modo de segurança (_fallback_rules).
"""

from __future__ import annotations

import os
from datetime import datetime


def coletar_gatilhos_premium(culture_slug: str, limit: int = 5) -> list[dict]:
    """
    Busca gatilhos recentes de fontes premium usados no dossiê lateral.
    Reuters/Bloomberg podem vir de RSS/licença própria; aqui apenas lemos o cache normalizado.
    """
    try:
        from flv.db import query

        like = f"%{culture_slug}%"
        rows = query(
            """
            SELECT source, category, title, url, published_at, sentiment, sentiment_score, relevance_score
            FROM flv_news_global
            WHERE lower(source) IN ('reuters', 'bloomberg')
              AND (
                lower(title) LIKE lower(?)
                OR lower(COALESCE(summary, '')) LIKE lower(?)
                OR lower(COALESCE(related_commodities, '')) LIKE lower(?)
                OR category IN ('commodities', 'clima', 'geopolitica', 'logistica', 'economia', 'producao')
              )
            ORDER BY published_at DESC, COALESCE(relevance_score, ABS(COALESCE(sentiment_score, 0))) DESC
            LIMIT ?
            """,
            (like, like, like, int(limit)),
        )
        return [dict(r) for r in rows]
    except Exception:
        return []


def gerar_relatorio_previsao(culture_slug: str, terminal: str | None, features: list[dict], forecast_result: dict) -> str:
    if not features or not forecast_result or not forecast_result.get("forecast"):
        return "Sem dados suficientes para explicar a previsão."

    gatilhos_premium = coletar_gatilhos_premium(culture_slug)

    # Tentativa Gemini (não pode quebrar o sistema)
    try:
        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if api_key:
            return _gerar_relatorio_gemini(api_key, culture_slug, terminal, features, forecast_result, gatilhos_premium)
    except Exception:
        pass

    return _fallback_rules(culture_slug, terminal, features, forecast_result, gatilhos_premium)


def _fallback_rules(
    culture_slug: str,
    terminal: str | None,
    features: list[dict],
    forecast_result: dict,
    gatilhos_premium: list[dict] | None = None,
) -> str:
    last = features[-1]
    trend = forecast_result.get("trend")
    target_price = forecast_result["forecast"][-1]["price"] if forecast_result.get("forecast") else None

    drivers = []

    # Notícias
    nri = float(last.get("news_risk_index") or 0.0)
    if nri >= 0.65:
        drivers.append("notícias globais com risco elevado (cadeia logística/geopolítica)")
    elif nri >= 0.35:
        drivers.append("noticiário com risco moderado (pressão em custos e fluxo)")

    # Diesel
    diesel = last.get("diesel_brl_l")
    diesel_chg = float(last.get("diesel_change_pct") or 0.0)
    if diesel_chg >= 1.0:
        drivers.append("alta recente do diesel (logística mais cara)")

    # Chuva (proxy)
    precip_7d = float(last.get("precip_7d") or 0.0)
    if precip_7d >= 70:
        drivers.append("chuvas acima do normal nas últimas semanas (risco de oferta/qualidade)")

    # Teleconexões
    oni = last.get("oni")
    if oni is not None:
        try:
            oni_f = float(oni)
            if oni_f >= 0.8:
                drivers.append("El Niño ativo (teleconexão elevando incerteza climática)")
            elif oni_f <= -0.8:
                drivers.append("La Niña ativa (teleconexão elevando incerteza climática)")
        except Exception:
            pass

    # USD
    usd = last.get("usd_brl")
    try:
        if usd is not None and float(usd) >= 5.5:
            drivers.append("câmbio mais estressado (insumos e energia sobem)")
    except Exception:
        pass

    if not drivers:
        drivers.append("padrões recentes de clima e preços históricos")

    gatilhos = []
    for item in (gatilhos_premium or [])[:3]:
        source = item.get("source") or "Fonte premium"
        title = item.get("title") or "gatilho sem título"
        gatilhos.append(f"{source}: {title}")

    price_txt = f"para R$ {target_price:.2f}" if target_price is not None else "para o patamar projetado"
    term_txt = f" no terminal {terminal}" if terminal else ""
    tr = "alta" if trend == "alta" else "baixa" if trend == "baixa" else "estabilidade"

    texto = (
        f"A projeção é de {tr} {price_txt}{term_txt} devido à combinação de "
        + ", ".join(drivers[:3])
        + "."
    )
    if gatilhos:
        texto += " Gatilhos Reuters/Bloomberg monitorados: " + " | ".join(gatilhos) + "."
    return texto


def _gerar_relatorio_gemini(
    api_key: str,
    culture_slug: str,
    terminal: str | None,
    features: list[dict],
    forecast_result: dict,
    gatilhos_premium: list[dict] | None = None,
) -> str:
    try:
        import google.generativeai as genai
    except Exception:
        return _fallback_rules(culture_slug, terminal, features, forecast_result, gatilhos_premium)

    last = features[-1]
    hist_tail = features[-14:] if len(features) >= 14 else features

    trend = forecast_result.get("trend")
    horizon = forecast_result.get("horizon_days")
    last_fc = forecast_result.get("forecast", [])[-1] if forecast_result.get("forecast") else None
    target_price = last_fc.get("price") if last_fc else None
    target_date = last_fc.get("date") if last_fc else None

    prompt = f"""
Você é um analista de mercado hortifruti (Brasil). Gere um relatório curto, objetivo e humano (3–6 frases),
em PT-BR, explicando a previsão de preço com base nos sinais abaixo. Evite jargão técnico e não invente fatos
fora dos dados. Se houver risco/logística/geopolítica/clima global, conecte com impacto em custo/fluxo/oferta.

Produto: {culture_slug}
Terminal: {terminal or "N/A"}
Tendência prevista: {trend}
Horizonte (dias): {horizon}
Preço-alvo: {target_price}
Data-alvo: {target_date}

Sinais recentes (última linha de features):
- precip_7d={last.get("precip_7d")}
- temp_max_avg={last.get("temp_max_avg")}
- ndvi={last.get("ndvi")}
- diesel_brl_l={last.get("diesel_brl_l")} diesel_change_pct={last.get("diesel_change_pct")}
- usd_brl={last.get("usd_brl")} selic_pct={last.get("selic_pct")} ipca_yoy_pct={last.get("ipca_yoy_pct")}
- news_risk_index={last.get("news_risk_index")}
- oni={last.get("oni")} atl_north_warm_idx={last.get("atl_north_warm_idx")}

Gatilhos Reuters/Bloomberg recentes (usar somente se relevantes):
{gatilhos_premium or []}

Histórico (últimos dias, formato ds,y + sinais):
{hist_tail}

Responda apenas com o texto final do relatório.
""".strip()

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.4,
                "top_p": 0.9,
                "max_output_tokens": 220,
            },
        )
        text = (getattr(resp, "text", None) or "").strip()
        if not text:
            return _fallback_rules(culture_slug, terminal, features, forecast_result, gatilhos_premium)
        # Guardrail simples: não deixar crescer demais
        if len(text) > 1200:
            text = text[:1200].rstrip() + "…"
        return text
    except Exception:
        return _fallback_rules(culture_slug, terminal, features, forecast_result, gatilhos_premium)
