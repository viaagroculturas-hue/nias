"""
IBGE SIDRA API — municípios e produção agrícola (PAM).
API pública, sem chave.
Documentação: https://apisidra.ibge.gov.br/
"""
import httpx
import logging
from typing import Any

logger = logging.getLogger(__name__)

BASE = "https://apisidra.ibge.gov.br/values"
LOCALIDADES = "https://servicodados.ibge.gov.br/api/v1/localidades"

# Tabelas PAM (Produção Agrícola Municipal)
# t5457 = área plantada, área colhida, quantidade produzida, rendimento, valor
PAM_TABELA = "5457"

CULTURAS_PAM = {
    # código IBGE → nome VIGÍA
    "40": "Arroz",
    "2713": "Feijão",
    "63": "Milho",
    "107": "Soja",
    "110": "Trigo",
    "7064": "Cana-de-açúcar",
    "213": "Mandioca",
    "79": "Algodão",
    "215": "Tomate",
    "216": "Batata",
    "41": "Banana",
    "214": "Laranja",
}


async def get_municipios_brasil() -> list[dict]:
    """Retorna todos os municípios BR com UF."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{LOCALIDADES}/municipios?orderBy=nome")
        r.raise_for_status()
        dados = r.json()

    return [
        {
            "nome": m["nome"],
            "codigo_ibge": str(m["id"]),
            "estado": m["microrregiao"]["mesorregiao"]["UF"]["sigla"],
            "estado_nome": m["microrregiao"]["mesorregiao"]["UF"]["nome"],
            "pais": "BRA",
            "regiao_agricola": m["microrregiao"]["nome"],
        }
        for m in dados
    ]


async def get_producao_municipal(
    cultura_codigo: str,
    ano: int = 2023,
    estados: list[str] = None,
) -> list[dict]:
    """
    PAM — produção agrícola municipal por cultura.
    Variáveis: 214=área plantada, 216=qtd produzida, 112=valor
    """
    # N6 = nível municipal, V214+V216+V112, período = ano
    filtro_estados = ""
    if estados:
        codigos = await _get_codigos_estados(estados)
        filtro_estados = f"/N3/{','.join(codigos)}"

    url = (
        f"{BASE}/t{PAM_TABELA}"
        f"/N6/all"
        f"/V214,216,112"
        f"/P/{ano}"
        f"/C782/{cultura_codigo}"
        f"?formato=json&decimais=2"
    )

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.get(url)
            if r.status_code != 200:
                logger.warning(f"IBGE PAM status {r.status_code} para cultura {cultura_codigo}")
                return []
            dados = r.json()
    except Exception as e:
        logger.error(f"IBGE PAM erro: {e}")
        return []

    # Primeiro item é cabeçalho
    if not dados or len(dados) < 2:
        return []

    resultado = []
    for row in dados[1:]:
        try:
            resultado.append({
                "municipio_codigo": row.get("D2C"),
                "municipio_nome": row.get("D2N"),
                "estado": row.get("D1N", "")[:2] if row.get("D1N") else "",
                "cultura_codigo": cultura_codigo,
                "ano": ano,
                "area_plantada_ha": _to_float(row.get("V214")),
                "producao_t": _to_float(row.get("V216")),
                "valor_mil_reais": _to_float(row.get("V112")),
                "fonte": "IBGE-SIDRA-PAM",
            })
        except Exception:
            continue

    return resultado


async def get_estados() -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{LOCALIDADES}/estados?orderBy=nome")
        r.raise_for_status()
        return r.json()


async def _get_codigos_estados(siglas: list[str]) -> list[str]:
    estados = await get_estados()
    return [str(e["id"]) for e in estados if e["sigla"] in siglas]


def _to_float(v: Any) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(".", "").replace(",", "."))
    except (ValueError, TypeError):
        return None
