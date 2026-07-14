from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.demanda import FatorDemanda, EventoCalendario

router = APIRouter()


@router.get("/fatores")
async def get_fatores(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FatorDemanda).where(FatorDemanda.ativo == True)
    )
    fatores = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "nome": f.nome,
            "tipo": f.tipo,
            "impacto_direcao": f.impacto_direcao,
            "impacto_pct": float(f.impacto_pct) if f.impacto_pct else None,
            "culturas_afetadas": f.culturas_afetadas,
            "paises_afetados": f.paises_afetados,
            "classes_renda_afetadas": f.classes_renda_afetadas,
            "periodo_inicio": f.periodo_inicio.isoformat() if f.periodo_inicio else None,
            "periodo_fim": f.periodo_fim.isoformat() if f.periodo_fim else None,
            "fonte_dado": f.fonte_dado,
            "confianca_pct": float(f.confianca_pct) if f.confianca_pct else None,
        }
        for f in fatores
    ]


@router.get("/eventos")
async def get_eventos(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(EventoCalendario).order_by(EventoCalendario.data_inicio)
    )
    eventos = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "nome": e.nome,
            "tipo": e.tipo,
            "pais": e.pais,
            "data_inicio": e.data_inicio.isoformat() if e.data_inicio else None,
            "data_fim": e.data_fim.isoformat() if e.data_fim else None,
            "direcao": e.direcao,
            "magnitude": e.magnitude,
            "culturas_afetadas": e.culturas_afetadas,
        }
        for e in eventos
    ]
