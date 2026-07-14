from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.pragas import PragaDoenca, OcorrenciaFitossanitaria

router = APIRouter()


@router.get("/")
async def get_pragas(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PragaDoenca).order_by(PragaDoenca.nome_comum))
    return [
        {
            "id": str(p.id),
            "nome_comum": p.nome_comum,
            "nome_cientifico": p.nome_cientifico,
            "tipo": p.tipo,
            "culturas_afetadas": p.culturas_afetadas,
            "perda_potencial_pct": float(p.perda_potencial_pct) if p.perda_potencial_pct else None,
            "janela_acao_horas": p.janela_acao_horas,
        }
        for p in result.scalars().all()
    ]


@router.get("/ocorrencias")
async def get_ocorrencias(nivel_risco: str = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(OcorrenciaFitossanitaria).order_by(OcorrenciaFitossanitaria.data_deteccao.desc())
    if nivel_risco:
        q = q.where(OcorrenciaFitossanitaria.nivel_risco == nivel_risco)
    result = await db.execute(q.limit(limit))
    return [
        {
            "id": str(o.id),
            "nivel_risco": o.nivel_risco,
            "area_afetada_pct": float(o.area_afetada_pct) if o.area_afetada_pct else None,
            "acao_recomendada": o.acao_recomendada,
            "data_deteccao": o.data_deteccao.isoformat() if o.data_deteccao else None,
        }
        for o in result.scalars().all()
    ]
