"""
INMET — Instituto Nacional de Meteorologia.
API pública: https://apitempo.inmet.gov.br/
566 estações automáticas + previsão por município.
Sem chave de API necessária.
"""
import httpx
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

BASE = "https://apitempo.inmet.gov.br"


async def get_estacoes() -> list[dict]:
    """Lista todas as estações automáticas (566 BR)."""
    url = f"{BASE}/estacoes/T"   # T = automáticas
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            r.raise_for_status()
            dados = r.json()
            return [
                {
                    "codigo": e.get("CD_ESTACAO"),
                    "nome": e.get("DC_NOME"),
                    "estado": e.get("SG_ESTADO"),
                    "lat": _to_float(e.get("VL_LATITUDE")),
                    "lon": _to_float(e.get("VL_LONGITUDE")),
                    "altitude_m": _to_float(e.get("VL_ALTITUDE")),
                    "tipo": "automatica",
                }
                for e in dados
            ]
    except Exception as e:
        logger.error(f"INMET estações erro: {e}")
        return []


async def get_dados_estacao(
    codigo: str,
    data_ini: date,
    data_fim: date,
) -> list[dict]:
    """Dados horários de uma estação no período."""
    url = (
        f"{BASE}/estacao/{data_ini.strftime('%Y-%m-%d')}/"
        f"{data_fim.strftime('%Y-%m-%d')}/{codigo}"
    )
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return []
            dados = r.json()
            return [_normalizar_medicao(d) for d in dados if d]
    except Exception as e:
        logger.error(f"INMET estação {codigo} erro: {e}")
        return []


async def get_previsao_municipio(codigo_ibge: str) -> dict | None:
    """
    Previsão 7 dias por município (código IBGE 7 dígitos).
    Endpoint: /condicao/municipio/{codigo}
    """
    url = f"{BASE}/previsao/{codigo_ibge}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            dados = r.json()
            if not dados:
                return None
            return {
                "municipio_codigo": codigo_ibge,
                "previsoes": [_normalizar_previsao(d) for d in dados],
                "fonte": "INMET",
            }
    except Exception as e:
        logger.error(f"INMET previsão {codigo_ibge} erro: {e}")
        return None


async def get_condicao_ponto(lat: float, lon: float) -> dict | None:
    """Condição atual mais próxima de um ponto (lat/lon)."""
    hoje = date.today().strftime("%Y-%m-%d")
    url = f"{BASE}/condicao/ponto/{lat}/{lon}/{hoje}/{hoje}"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return None
            dados = r.json()
            if not dados:
                return None
            ultimo = dados[-1] if isinstance(dados, list) else dados
            return {
                "lat": lat,
                "lon": lon,
                "temp_max": _to_float(ultimo.get("TEM_MAX")),
                "temp_min": _to_float(ultimo.get("TEM_MIN")),
                "precipitacao_mm": _to_float(ultimo.get("CHUVA")),
                "umidade_pct": _to_float(ultimo.get("UMD_MED")),
                "vento_km_h": _to_float(ultimo.get("VEN_VEL")),
                "data": hoje,
                "fonte": "INMET",
            }
    except Exception as e:
        logger.error(f"INMET ponto erro: {e}")
        return None


async def get_dados_recentes_estado(
    estado: str,
    dias: int = 7,
) -> list[dict]:
    """Dados das últimas N semanas para um estado."""
    estacoes = await get_estacoes()
    estacoes_estado = [e for e in estacoes if e["estado"] == estado]

    data_fim = date.today()
    data_ini = data_fim - timedelta(days=dias)

    resultados = []
    for estacao in estacoes_estado[:10]:   # limite para não sobrecarregar
        dados = await get_dados_estacao(
            estacao["codigo"], data_ini, data_fim
        )
        for d in dados:
            d["estacao_codigo"] = estacao["codigo"]
            d["estacao_nome"] = estacao["nome"]
            d["lat"] = estacao["lat"]
            d["lon"] = estacao["lon"]
        resultados.extend(dados)

    return resultados


def _normalizar_medicao(d: dict) -> dict:
    return {
        "data": d.get("DT_MEDICAO"),
        "hora": d.get("HR_MEDICAO"),
        "temp_c": _to_float(d.get("TEM_INS")),
        "temp_max": _to_float(d.get("TEM_MAX")),
        "temp_min": _to_float(d.get("TEM_MIN")),
        "umidade_pct": _to_float(d.get("UMD_INS")),
        "precipitacao_mm": _to_float(d.get("CHUVA")),
        "vento_km_h": _to_float(d.get("VEN_VEL")),
        "pressao_hpa": _to_float(d.get("PRE_INS")),
        "fonte": "INMET",
    }


def _normalizar_previsao(d: dict) -> dict:
    return {
        "data": d.get("data"),
        "condicao": d.get("condicao"),
        "temp_max": _to_float(d.get("temp_max")),
        "temp_min": _to_float(d.get("temp_min")),
        "chuva_mm": _to_float(d.get("chuva")),
        "umidade_max": _to_float(d.get("umidade_max")),
        "umidade_min": _to_float(d.get("umidade_min")),
        "fonte": "INMET",
    }


def _to_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except (ValueError, TypeError):
        return None
