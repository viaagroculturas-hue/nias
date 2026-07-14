"""
MDIC Comex Stat — exportações/importações BR.
API pública: http://api.comexstat.mdic.gov.br/
Sem chave necessária.
"""
import httpx
import logging
from datetime import date

logger = logging.getLogger(__name__)

BASE = "http://api.comexstat.mdic.gov.br"

# NCM agrícolas relevantes
NCM_AGRICOLA = {
    "1201": "Soja em grão",
    "1507": "Óleo de soja",
    "2302": "Farelo de soja",
    "1005": "Milho",
    "0901": "Café",
    "1701": "Açúcar bruto",
    "1702": "Açúcar refinado",
    "5201": "Algodão",
    "1006": "Arroz",
    "1001": "Trigo",
    "0803": "Banana",
    "0805": "Citros",
    "2207": "Álcool etílico",
}


async def get_exportacoes_produto(
    ncm: str,
    ano_ini: int = None,
    ano_fim: int = None,
) -> list[dict]:
    """Exportações por NCM — valores FOB em USD, peso kg."""
    if ano_ini is None:
        ano_ini = date.today().year - 1
    if ano_fim is None:
        ano_fim = date.today().year

    url = f"{BASE}/general"
    payload = {
        "flow": "Export",
        "monthDetail": False,
        "period": {
            "from": f"{ano_ini}01",
            "to": f"{ano_fim}12",
        },
        "filters": [
            {"filter": "ncm", "values": [ncm]},
        ],
        "details": ["ncm"],
        "metrics": ["metricFOB", "metricKG"],
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload)
            if r.status_code != 200:
                logger.warning(f"MDIC exportações status {r.status_code}")
                return []
            dados = r.json()
            return [
                {
                    "ncm": ncm,
                    "produto": NCM_AGRICOLA.get(ncm, ncm),
                    "ano": d.get("year"),
                    "valor_fob_usd": float(d.get("metricFOB", 0) or 0),
                    "peso_kg": float(d.get("metricKG", 0) or 0),
                    "fonte": "MDIC-ComexStat",
                }
                for d in (dados.get("data") or [])
            ]
    except Exception as e:
        logger.error(f"MDIC NCM {ncm} erro: {e}")
        return []


async def get_balanca_agricola(ano: int = None) -> dict:
    """Resumo da balança comercial agrícola BR."""
    if ano is None:
        ano = date.today().year - 1

    total_export_usd = 0.0
    por_produto = []

    for ncm, produto in list(NCM_AGRICOLA.items())[:5]:   # top 5 para não sobrecarregar
        dados = await get_exportacoes_produto(ncm, ano, ano)
        if dados:
            valor = sum(d["valor_fob_usd"] for d in dados)
            total_export_usd += valor
            por_produto.append({"ncm": ncm, "produto": produto, "valor_fob_usd": valor})

    return {
        "ano": ano,
        "total_export_usd": total_export_usd,
        "por_produto": sorted(por_produto, key=lambda x: x["valor_fob_usd"], reverse=True),
        "fonte": "MDIC-ComexStat",
    }
