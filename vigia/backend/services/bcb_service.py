"""
Banco Central do Brasil — API pública, sem chave.
Séries temporais: câmbio, SELIC, IPCA.
https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados
"""
import httpx
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"

# Códigos das séries
SERIES = {
    "usd_brl":    10813,   # Dólar comercial compra
    "eur_brl":    21619,   # Euro
    "selic":      11,      # Taxa SELIC
    "ipca":       433,     # IPCA mensal
    "igpm":       189,     # IGP-M mensal
    "credito_rural": 17637, # Concessões crédito rural total
}


async def get_ultima(serie: str) -> dict | None:
    """Pega o último valor disponível da série."""
    codigo = SERIES.get(serie)
    if not codigo:
        logger.warning(f"Série BCB desconhecida: {serie}")
        return None

    url = f"{BASE}.{codigo}/dados/ultimos/1?formato=json"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            r.raise_for_status()
            dados = r.json()
            if not dados:
                return None
            return {
                "serie": serie,
                "codigo": codigo,
                "data": dados[0]["data"],
                "valor": float(dados[0]["valor"].replace(",", ".")),
                "fonte": "BCB-SGS",
            }
    except Exception as e:
        logger.error(f"BCB série {serie} erro: {e}")
        return None


async def get_serie_historica(serie: str, dias: int = 365) -> list[dict]:
    """Histórico dos últimos N dias."""
    codigo = SERIES.get(serie)
    if not codigo:
        return []

    data_inicio = (date.today() - timedelta(days=dias)).strftime("%d/%m/%Y")
    data_fim = date.today().strftime("%d/%m/%Y")
    url = f"{BASE}.{codigo}/dados?formato=json&dataInicial={data_inicio}&dataFinal={data_fim}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            r.raise_for_status()
            dados = r.json()
            return [
                {
                    "data": d["data"],
                    "valor": float(d["valor"].replace(",", ".")),
                    "fonte": "BCB-SGS",
                }
                for d in dados
            ]
    except Exception as e:
        logger.error(f"BCB histórico {serie} erro: {e}")
        return []


async def get_cambio_atual() -> dict:
    """USD/BRL + EUR/BRL + ARS/BRL em tempo real."""
    usd = await get_ultima("usd_brl")
    eur = await get_ultima("eur_brl")

    # ARS/BRL: calculado via USD — BCB não tem série direta
    ars_brl = None
    if usd and usd["valor"]:
        # 1 ARS ≈ 0.001 USD (aprox) → ARS/BRL = ARS/USD × USD/BRL
        ars_brl = round(usd["valor"] / 1000, 6)

    return {
        "usd_brl": usd["valor"] if usd else None,
        "eur_brl": eur["valor"] if eur else None,
        "ars_brl": ars_brl,
        "data": usd["data"] if usd else None,
        "fonte": "BCB-SGS",
    }
