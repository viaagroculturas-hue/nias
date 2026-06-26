"""NIAS - Narrative API: gera narrativa de mercado FLV via Claude."""
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

from flv.db import get_conn

_cache = {}
_CACHE_TTL = 3600  # 1 hora


def _fetch_db_data():
    conn = get_conn()
    precos = []
    alertas = []
    polos = []

    try:
        rows = conn.execute(
            "SELECT culture_slug, AVG(price_brl) as avg_price "
            "FROM flv_prices WHERE date >= date('now','-3 days') "
            "GROUP BY culture_slug LIMIT 5"
        ).fetchall()
        precos = [dict(r) for r in rows]
    except Exception:
        pass

    try:
        rows = conn.execute(
            "SELECT severity, COUNT(*) as cnt FROM flv_alerts "
            "WHERE created_at >= datetime('now','-24 hours') GROUP BY severity"
        ).fetchall()
        alertas = [dict(r) for r in rows]
    except Exception:
        pass

    try:
        rows = conn.execute(
            "SELECT region_name, importance FROM sa_production_poles "
            "WHERE importance IN ('muito_alta','alta') LIMIT 5"
        ).fetchall()
        polos = [dict(r) for r in rows]
    except Exception:
        pass

    return precos, alertas, polos


def _build_prompt(precos, alertas, polos):
    p_str = json.dumps(precos, ensure_ascii=False) if precos else "sem dados de preços"
    a_str = json.dumps(alertas, ensure_ascii=False) if alertas else "sem alertas recentes"
    po_str = json.dumps(polos, ensure_ascii=False) if polos else "sem dados de polos"

    return (
        "Você é analista sênior de agronegócio da América do Sul. "
        f"Com base nos dados: preços CEASA recentes={p_str}, "
        f"alertas FLV últimas 24h={a_str}, "
        f"polos produtivos={po_str}. "
        "Gere em português: 1 parágrafo de narrativa de mercado (máx 80 palavras) "
        "e 3 bullets de ação imediata (máx 12 palavras cada). "
        'Formato JSON estrito: {"narrative":"...","bullets":["...","...","..."]}'
    )


def _call_claude(prompt):
    api_key = os.environ.get('ANTHROPIC_API_KEY', '') or os.environ.get('CLAUDE_API_KEY', '')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY não configurada")

    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST"
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read())

    text = result["content"][0]["text"].strip()
    # Extrai JSON do texto (Claude pode adicionar markdown)
    start = text.find('{')
    end = text.rfind('}') + 1
    if start >= 0 and end > start:
        text = text[start:end]
    return json.loads(text)


def handle_narrative(handler, path):
    try:
        now = time.time()
        cached = _cache.get('narrative')
        if cached and (now - cached['ts']) < _CACHE_TTL:
            data = json.dumps(cached['payload']).encode()
            handler.send_response(200)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(data)
            return

        precos, alertas, polos = _fetch_db_data()
        data_points = len(precos) + len(alertas) + len(polos)
        generated_at = datetime.now(timezone.utc).isoformat()

        if data_points == 0:
            payload = {
                "narrative": "Sem dados disponíveis no momento. O banco de dados está vazio ou não foi populado.",
                "bullets": [
                    "Aguardar ingestão de dados para análise.",
                    "Verificar conexão com fontes CONAB/CEASA.",
                    "Contatar suporte NIAS se o problema persistir."
                ],
                "generated_at": generated_at,
                "source": "fallback",
                "data_points": 0
            }
        else:
            prompt = _build_prompt(precos, alertas, polos)
            try:
                claude_resp = _call_claude(prompt)
                payload = {
                    "narrative": claude_resp.get("narrative", ""),
                    "bullets": claude_resp.get("bullets", []),
                    "generated_at": generated_at,
                    "source": "claude",
                    "data_points": data_points
                }
            except Exception as e:
                payload = {
                    "narrative": f"Claude indisponível ({e}). Dados reais encontrados: {data_points} pontos.",
                    "bullets": [
                        f"Preços disponíveis: {len(precos)} culturas.",
                        f"Alertas recentes: {len(alertas)} categorias.",
                        f"Polos produtivos mapeados: {len(polos)}."
                    ],
                    "generated_at": generated_at,
                    "source": "fallback",
                    "data_points": data_points
                }

        _cache['narrative'] = {'ts': now, 'payload': payload}

        out = json.dumps(payload).encode()
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(out)

    except Exception as e:
        err = json.dumps({'error': str(e)}).encode()
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)
