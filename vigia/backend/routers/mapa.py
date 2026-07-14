from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.geo import MunicipioSA
from models.satelite import MapeamentoSatelite
from models.clima import AlertaClimatico
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/municipios")
async def get_municipios(
    pais: str = None,
    limit: int = 500,
    db: AsyncSession = Depends(get_db),
):
    q = select(MunicipioSA)
    if pais:
        q = q.where(MunicipioSA.pais == pais)
    q = q.limit(limit)
    result = await db.execute(q)
    municipios = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "nome": m.nome,
            "estado": m.estado,
            "pais": m.pais,
            "lat": float(m.lat) if m.lat else None,
            "lon": float(m.lon) if m.lon else None,
            "regiao_agricola": m.regiao_agricola,
        }
        for m in municipios
    ]


@router.get("/mapeamentos")
async def get_mapeamentos(
    municipio_id: str = None,
    cultura: str = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(MapeamentoSatelite)
    if municipio_id:
        q = q.where(MapeamentoSatelite.municipio_id == municipio_id)
    if cultura:
        q = q.where(MapeamentoSatelite.cultura_detectada == cultura)
    q = q.order_by(MapeamentoSatelite.data_imagem.desc()).limit(limit)
    result = await db.execute(q)
    mapeamentos = result.scalars().all()

    return [
        {
            "id": str(m.id),
            "municipio_id": str(m.municipio_id),
            "cultura_detectada": m.cultura_detectada,
            "area_ha": float(m.area_ha) if m.area_ha else None,
            "ndvi_medio": float(m.ndvi_medio) if m.ndvi_medio else None,
            "fase_estimada": m.fase_estimada,
            "data_imagem": m.data_imagem.isoformat() if m.data_imagem else None,
            "anomalia_detectada": m.anomalia_detectada,
            "confianca_pct": float(m.confianca_pct) if m.confianca_pct else None,
        }
        for m in mapeamentos
    ]


@router.get("/alertas-geo")
async def get_alertas_geo(
    nivel: str = None,
    horas: int = 48,
    db: AsyncSession = Depends(get_db),
):
    """
    Alertas ativos com coordenadas do município — para plotar no mapa.
    Retorna apenas alertas com municipio_id que tenha lat/lon.
    """
    since = datetime.utcnow() - timedelta(hours=horas)
    q = (
        select(AlertaClimatico, MunicipioSA)
        .join(MunicipioSA, AlertaClimatico.municipio_id == MunicipioSA.id, isouter=True)
        .where(
            AlertaClimatico.status == "ativo",
            AlertaClimatico.created_at >= since,
            MunicipioSA.lat.isnot(None),
        )
    )
    if nivel:
        q = q.where(AlertaClimatico.nivel == nivel)
    q = q.order_by(AlertaClimatico.created_at.desc()).limit(500)

    result = await db.execute(q)
    rows = result.fetchall()

    return [
        {
            "id": str(a.id),
            "tipo": a.tipo,
            "nivel": a.nivel,
            "titulo": a.titulo,
            "descricao": a.descricao,
            "acao_recomendada": a.acao_recomendada,
            "confianca_pct": float(a.confianca_pct or 0),
            "impacto_financeiro": float(a.impacto_financeiro_estimado or 0),
            "fontes": a.fontes or [],
            "lat": float(m.lat) if m and m.lat else None,
            "lon": float(m.lon) if m and m.lon else None,
            "municipio": m.nome if m else None,
            "estado": m.estado if m else None,
            "pais": m.pais if m else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a, m in rows
        if m and m.lat
    ]


@router.get("/ndvi-geo")
async def get_ndvi_geo(
    anomalia: bool = False,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    """NDVI recente por município com coordenadas — camada satélite do mapa."""
    q = (
        select(MapeamentoSatelite, MunicipioSA)
        .join(MunicipioSA, MapeamentoSatelite.municipio_id == MunicipioSA.id)
        .where(MunicipioSA.lat.isnot(None))
        .order_by(MapeamentoSatelite.data_imagem.desc())
    )
    if anomalia:
        q = q.where(MapeamentoSatelite.anomalia_detectada == True)
    q = q.limit(limit)

    result = await db.execute(q)
    rows = result.fetchall()

    return [
        {
            "municipio_id": str(mp.municipio_id),
            "municipio": m.nome,
            "lat": float(m.lat),
            "lon": float(m.lon),
            "ndvi_medio": float(mp.ndvi_medio) if mp.ndvi_medio else None,
            "fase_estimada": mp.fase_estimada,
            "anomalia_detectada": mp.anomalia_detectada,
            "data_imagem": mp.data_imagem.isoformat() if mp.data_imagem else None,
            "satelite": mp.satelite,
        }
        for mp, m in rows
    ]
