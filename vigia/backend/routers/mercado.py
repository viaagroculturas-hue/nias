from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.mercado import CotacaoProduto, RotaLogistica
from models.clima import AlertaClimatico
from services.bcb_service import get_cambio_atual
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/cotacoes")
async def get_cotacoes(cultura_id: str = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(CotacaoProduto).order_by(CotacaoProduto.data_cotacao.desc())
    if cultura_id:
        q = q.where(CotacaoProduto.cultura_id == cultura_id)
    result = await db.execute(q.limit(limit))
    return [
        {
            "id": str(c.id),
            "praca": c.praca,
            "pais": c.pais,
            "preco": float(c.preco) if c.preco else None,
            "unidade": c.unidade,
            "data_cotacao": c.data_cotacao.isoformat() if c.data_cotacao else None,
            "variacao_pct": float(c.variacao_pct) if c.variacao_pct else None,
            "tendencia": c.tendencia,
            "fonte": c.fonte,
        }
        for c in result.scalars().all()
    ]


@router.get("/cambio")
async def get_cambio():
    """USD/BRL + EUR/BRL + ARS/BRL em tempo real — BCB SGS."""
    try:
        return await get_cambio_atual()
    except Exception as e:
        logger.error(f"Câmbio BCB erro: {e}")
        return {"usd_brl": None, "eur_brl": None, "ars_brl": None, "fonte": "BCB-SGS"}


@router.get("/rotas")
async def get_rotas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RotaLogistica).where(RotaLogistica.status == "ativo").limit(50))
    return [
        {
            "id": str(r.id),
            "origem": r.origem,
            "destino": r.destino,
            "tipo": r.tipo,
            "frete_por_tonelada": float(r.frete_por_tonelada) if r.frete_por_tonelada else None,
            "tempo_transito_h": float(r.tempo_transito_h) if r.tempo_transito_h else None,
        }
        for r in result.scalars().all()
    ]
