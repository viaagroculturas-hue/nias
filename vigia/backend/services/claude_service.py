import anthropic
from config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


async def gerar_resumo_executivo(
    alertas: list,
    mercado: dict,
    clima: dict,
    enso: dict,
) -> str:
    criticos = [a for a in alertas if a.get("nivel") == "critico"]
    atencao = [a for a in alertas if a.get("nivel") == "atencao"]

    prompt = f"""Você é o VIGÍA — sistema de inteligência agroestratégica da América do Sul.
Gere o resumo executivo do relatório das 05h30 em português, direto e objetivo.
Máximo 3 parágrafos. Foco em ação, não em descrição.

DADOS DO DIA:
- Alertas críticos: {len(criticos)}
- Alertas atenção: {len(atencao)}
- Mercado: {mercado}
- Clima: {clima}
- ENSO: {enso}

Alertas críticos: {criticos[:3]}

Responda com o texto do resumo executivo apenas. Sem markdown. Sem cabeçalhos."""

    try:
        client = get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        logger.error(f"Claude resumo erro: {e}")
        return f"Sistema VIGÍA — {len(criticos)} alertas críticos ativos. Verifique o painel."


async def analisar_risco_alerta(alerta_dict: dict) -> dict:
    prompt = f"""Analise este alerta agrícola e retorne JSON com:
- nivel_confirmado: info|atencao|critico|terra
- confianca_pct: número 0-100
- acao_recomendada: string concisa
- janela_horas: número inteiro
- justificativa: string curta

Alerta: {alerta_dict}

Responda APENAS com JSON válido."""

    try:
        client = get_client()
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        import json
        return json.loads(response.content[0].text)
    except Exception as e:
        logger.error(f"Claude análise erro: {e}")
        return {"nivel_confirmado": "atencao", "confianca_pct": 60, "justificativa": "erro IA"}
