"""
Multi-Agent API — Orquestra múltiplos agentes Claude especializados em paralelo.

Endpoints:
  POST /api/agents/dispatch   body: {query, context, agents}
  GET  /api/agents/status
"""
import json, os, time, threading
from datetime import datetime, timezone
import urllib.request

# ── Definição dos agentes ─────────────────────────────────────────────────────
AGENTS = {
    "clima":     {"role": "especialista em clima e meteorologia agrícola SA",        "max_tokens": 200},
    "preco":     {"role": "especialista em preços e mercados de commodities SA",     "max_tokens": 200},
    "logistica": {"role": "especialista em logística e supply chain agrícola SA",    "max_tokens": 200},
    "risco":     {"role": "especialista em risco legal e crédito agrícola",          "max_tokens": 150},
    "safra":     {"role": "especialista em safras e produção agrícola SA",           "max_tokens": 200},
}

MODEL_HAIKU    = "claude-haiku-4-5-20251001"
MODEL_SONNET   = "claude-sonnet-4-6"
ANTHROPIC_URL  = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VER  = "2023-06-01"

_STATS = {"calls_today": 0, "last_reset": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
_STATS_LOCK = threading.Lock()


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_api_key():
    return os.environ.get("ANTHROPIC_API_KEY", "")


def _call_claude(model, system_prompt, user_message, max_tokens):
    """Chama a API Claude via urllib. Retorna texto da resposta ou lança exceção."""
    api_key = _get_api_key()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY não configurada")

    payload = json.dumps({
        "model":      model,
        "max_tokens": max_tokens,
        "system":     system_prompt,
        "messages":   [{"role": "user", "content": user_message}],
    }).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": ANTHROPIC_VER,
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    content = body.get("content", [])
    for block in content:
        if block.get("type") == "text":
            return block["text"].strip()
    return ""


def _run_sub_agent(agent_name, agent_cfg, query, context, out_dict, errors_dict):
    """Worker de thread: chama Haiku como sub-agente especializado."""
    try:
        system = (
            f"Você é um {agent_cfg['role']} da plataforma NIAS. "
            "Responda de forma objetiva, técnica e concisa em português. "
            "Foque apenas na sua área de especialidade."
        )
        user_msg = f"CONSULTA: {query}"
        if context:
            user_msg += f"\n\nCONTEXTO ADICIONAL: {context}"

        answer = _call_claude(MODEL_HAIKU, system, user_msg, agent_cfg["max_tokens"])
        out_dict[agent_name] = answer
    except Exception as e:
        errors_dict[agent_name] = str(e)
        out_dict[agent_name] = f"[Indisponível: {e}]"


def _orchestrate(query, context, agent_responses):
    """Sonnet sintetiza as respostas dos sub-agentes."""
    parts = []
    for agent, resp in agent_responses.items():
        parts.append(f"[{agent.upper()}]: {resp}")

    synthesis_prompt = "\n\n".join(parts)
    system = (
        "Você é o orquestrador da plataforma NIAS — inteligência agrícola para a América do Sul. "
        "Receba as análises de múltiplos especialistas e sintetize uma resposta unificada, "
        "coerente e acionável em português. Seja direto e priorize informações críticas."
    )
    user_msg = (
        f"CONSULTA ORIGINAL: {query}\n\n"
        f"ANÁLISES ESPECIALIZADAS:\n{synthesis_prompt}\n\n"
        "Sintetize as análises em uma resposta integrada e acionável."
    )
    return _call_claude(MODEL_SONNET, system, user_msg, 400)


def _send_json(handler, code, obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def _read_body(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length:
        return json.loads(handler.rfile.read(length).decode("utf-8"))
    return {}


def handle_agents_dispatch(handler, path):
    try:
        t0 = time.time()
        body = _read_body(handler)

        query   = body.get("query", "").strip()
        context = body.get("context", "")
        agents_req = body.get("agents")  # lista ou None → usa todos

        if not query:
            _send_json(handler, 400, {"error": "Campo 'query' obrigatório"})
            return

        # Seleciona agentes
        if agents_req and isinstance(agents_req, list):
            selected = {k: v for k, v in AGENTS.items() if k in agents_req}
        else:
            selected = AGENTS

        if not selected:
            _send_json(handler, 400, {"error": "Nenhum agente válido selecionado"})
            return

        # Executa sub-agentes em paralelo
        responses = {}
        errors    = {}
        threads   = []

        for name, cfg in selected.items():
            t = threading.Thread(
                target=_run_sub_agent,
                args=(name, cfg, query, context, responses, errors),
                daemon=True,
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=18)

        # Síntese com Sonnet
        synthesis = ""
        synthesis_error = None
        try:
            synthesis = _orchestrate(query, context, responses)
        except Exception as e:
            synthesis_error = str(e)
            synthesis = "Síntese indisponível — ver respostas individuais dos agentes."

        latency_ms = int((time.time() - t0) * 1000)

        with _STATS_LOCK:
            _STATS["calls_today"] += 1

        result = {
            "query":           query,
            "agent_responses": responses,
            "synthesis":       synthesis,
            "agents_used":     len(responses),
            "latency_ms":      latency_ms,
            "generated_at":    _now_iso(),
        }
        if errors:
            result["agent_errors"] = errors
        if synthesis_error:
            result["synthesis_error"] = synthesis_error

        _send_json(handler, 200, result)

    except Exception as e:
        _send_json(handler, 500, {"error": str(e)})


def handle_agents_status(handler, path):
    try:
        api_key = _get_api_key()
        with _STATS_LOCK:
            calls = _STATS["calls_today"]
            last_reset = _STATS["last_reset"]

        result = {
            "available_agents": list(AGENTS.keys()),
            "agent_details": {
                k: {"role": v["role"], "max_tokens": v["max_tokens"]}
                for k, v in AGENTS.items()
            },
            "api_configured":   bool(api_key),
            "model_subagents":  MODEL_HAIKU,
            "model_orchestrator": MODEL_SONNET,
            "calls_today":      calls,
            "stats_since":      last_reset,
            "checked_at":       _now_iso(),
        }
        _send_json(handler, 200, result)
    except Exception as e:
        _send_json(handler, 500, {"error": str(e)})


def handle_multi_agent(handler, path):
    """Roteador principal para /api/agents/*"""
    method = handler.command

    if path.startswith("/api/agents/dispatch") and method == "POST":
        handle_agents_dispatch(handler, path)
    elif path.startswith("/api/agents/status"):
        handle_agents_status(handler, path)
    else:
        _send_json(handler, 404, {"error": "Endpoint não encontrado"})
