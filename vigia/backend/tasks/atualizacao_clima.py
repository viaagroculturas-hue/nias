"""
Coleta de dados climáticos: INMET (BR) + NOAA ENSO.
Roda 2x/dia: 06h e 18h.
"""
import asyncio
import logging
from celery import shared_task
from database import AsyncSessionLocal
from models.clima import EventoClimatico, AlertaEnso
from models.geo import MunicipioSA
from services.inmet_service import get_condicao_ponto, get_estacoes
from services.noaa_service import get_enso_completo
from sqlalchemy import select

logger = logging.getLogger(__name__)

# Estados prioritários para monitoramento intensivo
ESTADOS_PRIORIDADE = ["MT", "PR", "RS", "GO", "MG", "BA", "SP", "MS", "TO", "PA"]


@shared_task(name="tasks.atualizacao_clima.atualizar_clima")
def atualizar_clima():
    asyncio.run(_atualizar_clima())


@shared_task(name="tasks.atualizacao_clima.atualizar_enso")
def atualizar_enso():
    asyncio.run(_atualizar_enso())


async def _atualizar_clima():
    async with AsyncSessionLocal() as db:
        # Amostra de municípios representativos por estado
        result = await db.execute(
            select(MunicipioSA)
            .where(
                MunicipioSA.pais == "BRA",
                MunicipioSA.estado.in_(ESTADOS_PRIORIDADE),
                MunicipioSA.lat.isnot(None),
                MunicipioSA.lon.isnot(None),
            )
            .limit(100)
        )
        municipios = result.scalars().all()

        coletados = 0
        erros = 0
        for municipio in municipios:
            try:
                dados = await get_condicao_ponto(
                    float(municipio.lat), float(municipio.lon)
                )
                if not dados:
                    continue

                # Registrar como evento climático se há precipitação ou temperatura extrema
                precip = dados.get("precipitacao_mm") or 0
                temp_max = dados.get("temp_max")
                temp_min = dados.get("temp_min")

                eh_evento = (
                    precip > 30 or
                    (temp_max and temp_max > 38) or
                    (temp_min and temp_min < 5)
                )

                if eh_evento:
                    tipo = _classificar_evento(precip, temp_max, temp_min)
                    evento = EventoClimatico(
                        municipio_id=municipio.id,
                        tipo=tipo,
                        intensidade=_intensidade(precip, temp_max),
                        precipitacao_mm=precip if precip > 0 else None,
                        temperatura_max=temp_max,
                        temperatura_min=temp_min,
                        umidade_pct=dados.get("umidade_pct"),
                        vento_km_h=dados.get("vento_km_h"),
                        fonte="INMET",
                    )
                    db.add(evento)
                    coletados += 1

            except Exception as e:
                erros += 1
                logger.debug(f"Clima {municipio.nome} erro: {e}")

        await db.commit()
        logger.info(f"Clima atualizado: {coletados} eventos, {erros} erros, {len(municipios)} municípios")


async def _atualizar_enso():
    async with AsyncSessionLocal() as db:
        enso = await get_enso_completo()
        if not enso.get("disponivel"):
            logger.warning("ENSO não disponível")
            return

        alerta = AlertaEnso(
            tipo_enso=enso.get("tipo_enso", "neutro"),
            oni_index=enso.get("oni_index"),
            probabilidade_pct=enso.get("prob_el_nino") or enso.get("prob_la_nina"),
            periodo_previsto=enso.get("periodo"),
            regioes_impactadas=enso.get("impacto_regional"),
            culturas_em_risco=enso.get("impacto_regional", {}).get("culturas_risco", []),
            culturas_beneficiadas=[],
            recomendacoes=_recomendacoes_enso(enso),
            nivel_alerta=enso.get("nivel_alerta", "info"),
            fonte="NOAA-CPC",
        )
        db.add(alerta)
        await db.commit()
        logger.info(f"ENSO atualizado: {enso.get('tipo_enso')} ONI={enso.get('oni_index')}")


def _classificar_evento(precip: float, temp_max: float, temp_min: float) -> str:
    if precip > 80:
        return "chuva_intensa"
    if precip > 30:
        return "chuva_moderada"
    if temp_max and temp_max > 40:
        return "onda_calor"
    if temp_max and temp_max > 38:
        return "calor_intenso"
    if temp_min and temp_min < 0:
        return "geada"
    if temp_min and temp_min < 5:
        return "frio_intenso"
    return "evento_climatico"


def _intensidade(precip: float, temp_max: float) -> str:
    if precip > 100 or (temp_max and temp_max > 42):
        return "extremo"
    if precip > 50 or (temp_max and temp_max > 40):
        return "forte"
    return "moderado"


def _recomendacoes_enso(enso: dict) -> list[str]:
    tipo = enso.get("tipo_enso", "neutro")
    recomendacoes = []

    if "el_nino" in tipo:
        recomendacoes = [
            "Preparar drenagem para excesso de chuva no Sul do BR e Argentina",
            "Monitorar fungos foliares em soja e trigo (umidade alta)",
            "Avaliar seguro agrícola para culturas no Nordeste (seca)",
            "Diversificar culturas resilientes à seca no Nordeste",
        ]
    elif "la_nina" in tipo:
        recomendacoes = [
            "Planejar irrigação suplementar para soja no RS e PR",
            "Monitorar estoque de água nas bacias do Sul",
            "Aproveitar previsão de chuva no Nordeste para cultivos de sequeiro",
            "Revisar seguros para soja argentina (seca nos Pampas)",
        ]
    else:
        recomendacoes = ["Condições neutras — monitoramento padrão"]

    return recomendacoes
