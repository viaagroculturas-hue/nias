from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models.satelite import MapeamentoSatelite

router = APIRouter()


@router.get("/ndvi/resumo")
async def get_ndvi_resumo(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            func.avg(MapeamentoSatelite.ndvi_medio).label("ndvi_medio_sa"),
            func.count(MapeamentoSatelite.id).label("total_mapeamentos"),
            func.sum(MapeamentoSatelite.area_ha).label("area_total_ha"),
        )
    )
    row = result.first()
    return {
        "ndvi_medio_sa": float(row.ndvi_medio_sa) if row.ndvi_medio_sa else None,
        "total_mapeamentos": row.total_mapeamentos or 0,
        "area_total_ha": float(row.area_total_ha) if row.area_total_ha else None,
    }


@router.get("/anomalias")
async def get_anomalias(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(MapeamentoSatelite)
        .where(MapeamentoSatelite.anomalia_detectada == True)
        .order_by(MapeamentoSatelite.data_imagem.desc())
        .limit(limit)
    )
    return [
        {
            "id": str(m.id),
            "municipio_id": str(m.municipio_id),
            "cultura_detectada": m.cultura_detectada,
            "ndvi_medio": float(m.ndvi_medio) if m.ndvi_medio else None,
            "z_score": float(m.z_score) if m.z_score else None,
            "data_imagem": m.data_imagem.isoformat() if m.data_imagem else None,
        }
        for m in result.scalars().all()
    ]
