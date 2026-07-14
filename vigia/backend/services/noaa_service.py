"""
NOAA CPC — Climate Prediction Center.
ENSO (El Niño / La Niña): índice ONI, previsões sazonais.
Dados públicos, sem chave.

Fontes SA fora do Brasil:
  - SMN Argentina: https://www.smn.gob.ar/
  - DMC Chile: https://climatologia.meteochile.gob.cl/
  - SENAMHI Peru: https://www.senamhi.gob.pe/
  - CPTEC/INPE Brasil: https://clima1.cptec.inpe.br/
"""
import httpx
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

NOAA_ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
NOAA_ENSO_PROB_URL = "https://www.cpc.ncep.noaa.gov/products/CFSv2/htmls/probabilities.html"
CPTEC_PREV_URL = "https://climate.cptec.inpe.br/precipitacao/pt"


async def get_oni_index() -> dict | None:
    """
    Índice ONI (Oceanic Niño Index) mais recente.
    Arquivo texto NOAA — atualizado mensalmente.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(NOAA_ONI_URL)
            if r.status_code != 200:
                logger.warning(f"NOAA ONI status {r.status_code}")
                return None

        linhas = r.text.strip().split("\n")
        # Formato: SEAS YR TOTAL ANOM
        ultimas = [l for l in linhas if l.strip() and not l.startswith("SEAS")]
        if not ultimas:
            return None

        ultima = ultimas[-1].split()
        periodo = ultima[0] if len(ultima) > 0 else "?"
        ano = ultima[1] if len(ultima) > 1 else "?"
        oni = float(ultima[3]) if len(ultima) > 3 else None

        tipo = _classificar_oni(oni)

        return {
            "periodo": f"{periodo}/{ano}",
            "oni_index": oni,
            "tipo_enso": tipo,
            "nivel_alerta": _nivel_alerta(oni),
            "fonte": "NOAA-CPC",
            "url": NOAA_ONI_URL,
        }
    except Exception as e:
        logger.error(f"NOAA ONI erro: {e}")
        return None


async def get_probabilidades_enso() -> dict | None:
    """
    Probabilidades de El Niño / La Niña / Neutro para os próximos 9 meses.
    NOAA CPC — publicado mensalmente.
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(NOAA_ENSO_PROB_URL)
            if r.status_code != 200:
                return None

        # Parse simples das probabilidades na página
        texto = r.text
        el_nino = _extrair_probabilidade(texto, r"El\s*Ni.o[^%]*?(\d+)\s*%", 0)
        la_nina = _extrair_probabilidade(texto, r"La\s*Ni.a[^%]*?(\d+)\s*%", 0)
        neutro = _extrair_probabilidade(texto, r"[Nn]eutro?[^%]*?(\d+)\s*%", 100 - el_nino - la_nina)

        return {
            "prob_el_nino": el_nino,
            "prob_la_nina": la_nina,
            "prob_neutro": neutro,
            "fonte": "NOAA-CPC",
        }
    except Exception as e:
        logger.error(f"NOAA probabilidades erro: {e}")
        return None


async def get_anomalia_precipitacao_sa() -> list[dict]:
    """
    Anomalias de precipitação para América do Sul.
    CPTEC/INPE — dados de satélite.
    """
    url = "https://clima1.cptec.inpe.br/monitoramentodoenso/pt"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.get(url)
            if r.status_code == 200:
                logger.info("CPTEC anomalias coletadas")
                return []  # Parser a ser implementado por estrutura da resposta
    except Exception as e:
        logger.error(f"CPTEC anomalias erro: {e}")
    return []


async def get_clima_argentina() -> dict | None:
    """SMN Argentina — boletim agrometeorológico."""
    url = "https://www.smn.gob.ar/sites/default/files/smn_campo/agrometeorologia/boletin_agrometeo.pdf"
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.head(url)
            return {
                "disponivel": r.status_code == 200,
                "url": url,
                "fonte": "SMN-ARG",
            }
    except Exception as e:
        logger.error(f"SMN Argentina erro: {e}")
        return None


async def get_enso_completo() -> dict:
    """Consolida ONI + probabilidades em um objeto."""
    oni = await get_oni_index()
    probs = await get_probabilidades_enso()

    resultado = {
        "disponivel": oni is not None,
        "fonte": "NOAA-CPC",
        "data_coleta": date.today().isoformat(),
    }

    if oni:
        resultado.update(oni)
    if probs:
        resultado.update(probs)

    # Impacto por região SA
    tipo = resultado.get("tipo_enso", "neutro")
    resultado["impacto_regional"] = _impacto_regional(tipo)

    return resultado


def _classificar_oni(oni: float | None) -> str:
    if oni is None:
        return "neutro"
    if oni >= 2.0:
        return "el_nino_forte"
    if oni >= 1.0:
        return "el_nino_moderado"
    if oni >= 0.5:
        return "el_nino_fraco"
    if oni <= -2.0:
        return "la_nina_forte"
    if oni <= -1.0:
        return "la_nina_moderada"
    if oni <= -0.5:
        return "la_nina_fraca"
    return "neutro"


def _nivel_alerta(oni: float | None) -> str:
    if oni is None:
        return "info"
    if abs(oni) >= 2.0:
        return "critico"
    if abs(oni) >= 1.0:
        return "atencao"
    if abs(oni) >= 0.5:
        return "info"
    return "info"


def _extrair_probabilidade(texto: str, pattern: str, default: float) -> float:
    match = re.search(pattern, texto, re.IGNORECASE)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            pass
    return default


def _impacto_regional(tipo_enso: str) -> dict:
    """
    Impactos históricos documentados por fase ENSO na América do Sul.
    Fonte: NOAA CPC + CPTEC + literatura científica.
    """
    base = {
        "sul_brasil": "normal",
        "centro_oeste_brasil": "normal",
        "nordeste_brasil": "normal",
        "pampas_argentina": "normal",
        "paraguai": "normal",
        "andes_peru_bolivia": "normal",
        "chile_central": "normal",
    }

    if "el_nino" in tipo_enso:
        intensidade = "forte" if "forte" in tipo_enso else "moderado"
        return {
            "sul_brasil": f"excesso_chuva_{intensidade}",
            "centro_oeste_brasil": "chuva_acima_normal",
            "nordeste_brasil": f"seca_{intensidade}",
            "pampas_argentina": "excesso_chuva",
            "paraguai": "excesso_chuva",
            "andes_peru_bolivia": "seca",
            "chile_central": "chuva_acima_normal",
            "risco_principal": "inundacoes_sul_brasil_e_argentina",
            "culturas_risco": ["soja_pr_rs", "trigo_argentina", "milho_nordeste"],
        }
    elif "la_nina" in tipo_enso:
        intensidade = "forte" if "forte" in tipo_enso else "moderado"
        return {
            "sul_brasil": f"seca_{intensidade}",
            "centro_oeste_brasil": "chuva_normal",
            "nordeste_brasil": "chuva_acima_normal",
            "pampas_argentina": f"seca_{intensidade}",
            "paraguai": "seca",
            "andes_peru_bolivia": "chuva_acima_normal",
            "chile_central": "seca",
            "risco_principal": "seca_pampas_e_sul_brasil",
            "culturas_risco": ["soja_argentina", "trigo_argentina", "soja_rs"],
        }
    return base
