import asyncio
import logging
from celery import shared_task
from database import AsyncSessionLocal
from models.demanda import FatorDemanda
from sqlalchemy import select

logger = logging.getLogger(__name__)


@shared_task(name="tasks.fatores_demanda.atualizar_fatores")
def atualizar_fatores():
    asyncio.get_event_loop().run_until_complete(_atualizar())


async def _atualizar():
    """Semanal — atualizar fatores de demanda dinâmicos (câmbio, Bets, etc.)."""
    async with AsyncSessionLocal() as db:
        await _atualizar_cambio(db)
        logger.info("Fatores de demanda atualizados")


async def _atualizar_cambio(db):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(
                "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/1?formato=json"
            )
            if r.status_code == 200:
                dados = r.json()
                if dados:
                    valor = float(dados[0]["valor"])
                    result = await db.execute(
                        select(FatorDemanda).where(FatorDemanda.nome == "Câmbio USD/BRL")
                    )
                    fator = result.scalar_one_or_none()
                    if fator:
                        fator.fonte_dado = f"BCB — USD/BRL {valor}"
                        await db.commit()
                        logger.info(f"Câmbio atualizado: {valor}")
    except Exception as e:
        logger.error(f"Câmbio update erro: {e}")
