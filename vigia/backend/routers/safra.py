from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.safra import Safra, PrevisaoSafra
from models.cultura import Cultura

router = APIRouter()


@router.get("/")
async def get_safras(status: str = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(Safra)
    if status:
        q = q.where(Safra.status == status)
    result = await db.execute(q.order_by(Safra.data_plantio.desc()).limit(limit))
    return [
        {
            "id": str(s.id),
            "ano_safra": s.ano_safra,
            "status": s.status,
            "fase_atual": s.fase_atual,
            "area_plantada_ha": float(s.area_plantada_ha) if s.area_plantada_ha else None,
            "data_plantio": s.data_plantio.isoformat() if s.data_plantio else None,
            "data_colheita_prevista": s.data_colheita_prevista.isoformat() if s.data_colheita_prevista else None,
        }
        for s in result.scalars().all()
    ]


@router.get("/culturas")
async def get_culturas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cultura).order_by(Cultura.nome))
    return [
        {
            "id": str(c.id),
            "nome": c.nome,
            "categoria": c.categoria,
            "ciclo_dias_min": c.ciclo_dias_min,
            "ciclo_dias_max": c.ciclo_dias_max,
            "paises_producao": c.paises_producao,
        }
        for c in result.scalars().all()
    ]
