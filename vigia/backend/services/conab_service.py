"""
CONAB — Companhia Nacional de Abastecimento.
Safras e preços de referência.
API pública: https://portaldeinformacoes.conab.gov.br/
"""
import httpx
import logging
from datetime import date

logger = logging.getLogger(__name__)

BASE_PRECOS = "https://portaldeinformacoes.conab.gov.br/index.php/services"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VIGIA-bot/1.0)",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://portaldeinformacoes.conab.gov.br/",
}


async def get_levantamento_safra(
    produto: str = "soja",
    ano_safra: str = None,
) -> dict | None:
    """
    Levantamento de safra CONAB — área, produção, produtividade.
    Publicado mensalmente.
    """
    if ano_safra is None:
        hoje = date.today()
        ano_safra = f"{hoje.year-1}/{str(hoje.year)[2:]}"

    url = f"{BASE_PRECOS}/levantamento-safra"
    params = {"produto": produto, "safra": ano_safra, "formato": "json"}

    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.error(f"CONAB safra {produto} erro: {e}")

    return None


async def get_precos_agropecuarios(
    produto: str,
    estado: str = None,
    meses: int = 12,
) -> list[dict]:
    """
    Preços pagos ao produtor — série histórica.
    Endpoint do portal de informações CONAB.
    """
    url = f"{BASE_PRECOS}/precos-agropecuarios"
    params = {
        "produto": produto,
        "tipo": "mensal",
        "meses": meses,
    }
    if estado:
        params["estado"] = estado

    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                dados = r.json()
                if isinstance(dados, list):
                    return [
                        {
                            "produto": produto,
                            "periodo": d.get("periodo"),
                            "preco": _to_float(d.get("preco")),
                            "unidade": d.get("unidade", ""),
                            "estado": estado,
                            "fonte": "CONAB",
                        }
                        for d in dados
                    ]
    except Exception as e:
        logger.error(f"CONAB preços {produto} erro: {e}")

    return []


async def get_precos_minimos() -> list[dict]:
    """
    Preços mínimos de garantia (PGPM) — safra atual.
    Portaria MAPA/CONAB publicada anualmente.
    """
    url = "https://www.conab.gov.br/component/k2/item/download/18985_9a4f5a3e8c8e5d3a6b2a7f1c0e4d9b8a"
    # URL estável para planilha de preços mínimos — pode mudar a cada safra
    # Implementação: parsear JSON publicado pelo CONAB
    logger.info("CONAB preços mínimos: endpoint a ser configurado por safra")
    return []


def _to_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return None
