from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.inteligencia import RelatórioManha
from datetime import date

router = APIRouter()


@router.get("/hoje")
async def get_relatorio_hoje(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RelatórioManha)
        .where(RelatórioManha.data_referencia == date.today())
        .order_by(RelatórioManha.gerado_em.desc())
        .limit(1)
    )
    r = result.scalar_one_or_none()
    if not r:
        return {"disponivel": False, "message": "Relatório das 05h30 ainda não gerado para hoje"}

    return {
        "disponivel": True,
        "data_referencia": r.data_referencia.isoformat(),
        "gerado_em": r.gerado_em.isoformat() if r.gerado_em else None,
        "resumo_executivo": r.resumo_executivo,
        "alertas_criticos": r.alertas_criticos,
        "alertas_atencao": r.alertas_atencao,
        "oportunidades": r.oportunidades,
        "mercado_snapshot": r.mercado_snapshot,
        "clima_snapshot": r.clima_snapshot,
        "enso_snapshot": r.enso_snapshot,
        "acoes_do_dia": r.acoes_do_dia,
        "municipios_monitorados": r.municipios_monitorados,
        "alertas_gerados": r.alertas_gerados,
        "enviado_whatsapp": r.enviado_whatsapp,
    }


@router.get("/historico")
async def get_historico(limit: int = 30, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RelatórioManha)
        .order_by(RelatórioManha.data_referencia.desc())
        .limit(limit)
    )
    relatorios = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "data_referencia": r.data_referencia.isoformat(),
            "alertas_criticos": len(r.alertas_criticos or []),
            "municipios_monitorados": r.municipios_monitorados,
            "gerado_em": r.gerado_em.isoformat() if r.gerado_em else None,
        }
        for r in relatorios
    ]
