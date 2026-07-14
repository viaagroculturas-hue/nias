import asyncio
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="tasks.viveiros_seed.atualizar_viveiros")
def atualizar_viveiros():
    asyncio.get_event_loop().run_until_complete(_atualizar())


async def _atualizar():
    """Semanal — RENASEM/MAPA scraper (dados públicos)."""
    logger.info("Viveiros RENASEM: verificando atualizações")
    # RENASEM é scraping de página pública
    # Implementar com httpx + BeautifulSoup quando disponível
