from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.clima import EventoClimatico, PrevisaoClimatica, AlertaEnso

router = APIRouter()


@router.get("/eventos")
async def get_eventos(municipio_id: str = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(EventoClimatico).order_by(EventoClimatico.data_inicio.desc())
    if municipio_id:
        q = q.where(EventoClimatico.municipio_id == municipio_id)
    result = await db.execute(q.limit(limit))
    return [
        {
            "id": str(e.id),
            "tipo": e.tipo,
            "intensidade": e.intensidade,
            "precipitacao_mm": float(e.precipitacao_mm) if e.precipitacao_mm else None,
            "temperatura_max": float(e.temperatura_max) if e.temperatura_max else None,
            "data_inicio": e.data_inicio.isoformat() if e.data_inicio else None,
            "fonte": e.fonte,
        }
        for e in result.scalars().all()
    ]


@router.get("/enso")
async def get_enso(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AlertaEnso).order_by(AlertaEnso.created_at.desc()).limit(1)
    )
    enso = result.scalar_one_or_none()
    if not enso:
        return {"disponivel": False}
    return {
        "disponivel": True,
        "tipo_enso": enso.tipo_enso,
        "oni_index": float(enso.oni_index) if enso.oni_index else None,
        "probabilidade_pct": float(enso.probabilidade_pct) if enso.probabilidade_pct else None,
        "nivel_alerta": enso.nivel_alerta,
        "culturas_em_risco": enso.culturas_em_risco,
        "culturas_beneficiadas": enso.culturas_beneficiadas,
        "recomendacoes": enso.recomendacoes,
        "valido_ate": enso.valido_ate.isoformat() if enso.valido_ate else None,
        "fonte": enso.fonte,
    }
