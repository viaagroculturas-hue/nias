"""
Coleta de preços: CEPEA (scraper) + BCB (câmbio) + CONAB.
Roda diariamente às 08h.
"""
import asyncio
import logging
from celery import shared_task
from datetime import date
from database import AsyncSessionLocal
from models.cultura import Cultura
from models.mercado import CotacaoProduto
from models.demanda import FatorDemanda
from services.cepea_service import get_todas_cotacoes, PRODUTOS as CEPEA_PRODUTOS
from services.bcb_service import get_cambio_atual
from services.verificacao_service import verificar_simples
from sqlalchemy import select

logger = logging.getLogger(__name__)


@shared_task(name="tasks.atualizacao_precos.atualizar_precos")
def atualizar_precos():
    asyncio.run(_atualizar())


async def _atualizar():
    async with AsyncSessionLocal() as db:
        await _coletar_cepea(db)
        await _coletar_cambio(db)
        await db.commit()
        logger.info("Preços atualizados com sucesso")


async def _coletar_cepea(db):
    cotacoes = await get_todas_cotacoes()
    hoje = date.today()

    for cot in cotacoes:
        # Buscar cultura no banco
        result = await db.execute(
            select(Cultura).where(Cultura.nome.ilike(f"%{cot['produto'].split()[0]}%"))
        )
        cultura = result.scalar_one_or_none()

        # Verificar se já temos a cotação do dia
        if cultura:
            result = await db.execute(
                select(CotacaoProduto)
                .where(
                    CotacaoProduto.cultura_id == cultura.id,
                    CotacaoProduto.data_cotacao == hoje,
                    CotacaoProduto.fonte == "CEPEA-ESALQ",
                )
            )
            existente = result.scalar_one_or_none()
            if existente:
                existente.preco = cot["preco"]
                existente.variacao_pct = cot.get("variacao_pct")
                existente.tendencia = cot.get("tendencia")
                continue

        verificacao = verificar_simples(
            cot["preco"],
            [{"nome": "CEPEA-ESALQ", "valor": cot["preco"]}],
        )

        cotacao_obj = CotacaoProduto(
            cultura_id=cultura.id if cultura else None,
            praca=cot["praca"],
            pais="BRA",
            preco=cot["preco"],
            unidade=cot["unidade"],
            data_cotacao=hoje,
            variacao_pct=cot.get("variacao_pct"),
            tendencia=cot.get("tendencia", "estavel"),
            fonte="CEPEA-ESALQ",
            confianca_pct=verificacao["score_confianca"],
        )
        db.add(cotacao_obj)

    logger.info(f"CEPEA: {len(cotacoes)} cotações coletadas")


async def _coletar_cambio(db):
    cambio = await get_cambio_atual()
    if not cambio.get("usd_brl"):
        return

    # Atualizar fator de demanda "Câmbio USD/BRL"
    result = await db.execute(
        select(FatorDemanda).where(FatorDemanda.nome == "Câmbio USD/BRL")
    )
    fator = result.scalar_one_or_none()
    if fator:
        fator.fonte_dado = f"BCB — USD/BRL {cambio['usd_brl']:.3f} ({cambio.get('data', hoje)})"
        fator.impacto_pct = _calcular_impacto_cambio(cambio["usd_brl"])

    logger.info(f"BCB câmbio: USD/BRL {cambio['usd_brl']}")


def _calcular_impacto_cambio(usd_brl: float) -> float:
    """Dólar alto = commodities exportadas mais caras em BRL."""
    neutro = 5.0   # referência
    variacao = ((usd_brl - neutro) / neutro) * 100
    return round(min(max(variacao, -50), 50), 1)
