"""
Task Celery: executa todos os agentes a cada 2 horas.
Substitui o stub original — agora orquestra todos os 9 agentes.
"""
import asyncio
import logging
from celery import shared_task
from database import AsyncSessionLocal
from agents import executar_todos_agentes

logger = logging.getLogger(__name__)


@shared_task(name="tasks.verificacao_risco.verificar_riscos", bind=True, max_retries=2)
def verificar_riscos(self):
    """Ciclo completo de análise de risco — roda a cada 2h."""
    try:
        resultado = asyncio.run(_executar())
        logger.info(f"verificacao_risco: {resultado}")
        return resultado
    except Exception as exc:
        logger.error(f"verificacao_risco falhou: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=300)


async def _executar() -> dict:
    async with AsyncSessionLocal() as db:
        return await executar_todos_agentes(db)
