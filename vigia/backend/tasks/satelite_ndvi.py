"""
Task Celery: processa NDVI via Google Earth Engine para municípios prioritários.
Roda diariamente às 06h via Celery Beat.
"""
import asyncio
import logging
from celery import shared_task
from database import AsyncSessionLocal
from agents.agente_satelite import AgenteSatelite
from sqlalchemy import select
from models.geo import MunicipioSA

logger = logging.getLogger(__name__)

# Municípios priorizados por importância agrícola
MUNICIPIOS_PRIORITARIOS_IBGE = [
    "3548807",  # Sorriso/MT — maior produtor de soja
    "5107040",  # Nova Mutum/MT
    "5107065",  # Lucas do Rio Verde/MT
    "5002704",  # Dourados/MS
    "4106902",  # Cascavel/PR
    "4125506",  # Ponta Grossa/PR
    "3518800",  # Campinas/SP
    "3548906",  # São José do Rio Preto/SP
    "2927408",  # Barreiras/BA
    "1703206",  # Formosa do Rio Preto/BA
]


@shared_task(name="tasks.satelite_ndvi.processar_ndvi", bind=True, max_retries=1)
def processar_ndvi(self):
    """Calcula NDVI para municípios prioritários e detecta anomalias."""
    try:
        resultado = asyncio.run(_processar())
        logger.info(f"satelite_ndvi: {resultado}")
        return resultado
    except Exception as exc:
        logger.error(f"satelite_ndvi falhou: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=3600)


async def _processar() -> dict:
    async with AsyncSessionLocal() as db:
        # Buscar municípios por código IBGE prioritário
        result = await db.execute(
            select(MunicipioSA)
            .where(
                MunicipioSA.lat.isnot(None),
                MunicipioSA.pais == "BRA",
            )
            .limit(100)
        )
        municipios = result.scalars().all()

        agente = AgenteSatelite(db)
        alertas = await agente.executar(municipios=municipios)

        return {
            "municipios_processados": len(municipios),
            "anomalias_detectadas": len(alertas),
        }
