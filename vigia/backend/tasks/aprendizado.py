import asyncio
import logging
from celery import shared_task
from database import AsyncSessionLocal
from models.inteligencia import RecomendacaoVigia, AprendizadoVigia
from sqlalchemy import select

logger = logging.getLogger(__name__)


@shared_task(name="tasks.aprendizado.rodar_aprendizado")
def rodar_aprendizado():
    asyncio.get_event_loop().run_until_complete(_aprender())


async def _aprender():
    """Semanal — calcular acurácia das recomendações e ajustar parâmetros."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RecomendacaoVigia)
            .where(
                RecomendacaoVigia.status == "concluido",
                RecomendacaoVigia.resultado_real.isnot(None),
                RecomendacaoVigia.acuracia_pct.is_(None),
            )
        )
        recomendacoes = result.scalars().all()

        for rec in recomendacoes:
            aprend = AprendizadoVigia(
                recomendacao_id=rec.id,
                tipo_previsao=rec.tipo,
                valor_previsto={"impacto": float(rec.impacto_financeiro_estimado or 0)},
                valor_real={"resultado": rec.resultado_real},
            )
            db.add(aprend)

        await db.commit()
        logger.info(f"Aprendizado: {len(recomendacoes)} recomendações avaliadas")
