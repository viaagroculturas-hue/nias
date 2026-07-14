"""
GET /api/health — status completo do sistema VIGÍA.
Verifica banco, Redis, e conectividade com fontes externas.
"""
import asyncio
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, func
from database import get_db, engine
from models.geo import MunicipioSA
from models.cultura import Cultura
from models.inteligencia import SeedStatus
import httpx
import time

router = APIRouter()
logger = logging.getLogger(__name__)

FONTES_EXTERNAS = [
    ("IBGE",     "https://servicodados.ibge.gov.br/api/v1/localidades/regioes"),
    ("BCB",      "https://api.bcb.gov.br/dados/serie/bcdata.sgs.10813/dados/ultimos/1?formato=json"),
    ("INMET",    "https://apitempo.inmet.gov.br/estacoes/T"),
    ("NOAA-CPC", "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"),
    ("CEPEA",    "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx"),
    ("CONAB",    "https://www.conab.gov.br"),
    ("MDIC",     "http://api.comexstat.mdic.gov.br"),
]


@router.get("/")
async def health(db: AsyncSession = Depends(get_db)):
    inicio = time.time()
    checks = {}

    # Banco
    try:
        await db.execute(text("SELECT 1"))
        result = await db.execute(select(func.count(MunicipioSA.id)))
        municipios = result.scalar() or 0
        result2 = await db.execute(select(func.count(Cultura.id)))
        culturas = result2.scalar() or 0
        checks["banco"] = {
            "status": "ok",
            "municipios": municipios,
            "culturas": culturas,
        }
    except Exception as e:
        checks["banco"] = {"status": "erro", "detalhe": str(e)}

    # Seed status
    try:
        result = await db.execute(select(SeedStatus).order_by(SeedStatus.etapa))
        etapas = result.scalars().all()
        concluidas = sum(1 for e in etapas if e.status == "concluido")
        checks["seed"] = {
            "status": "ok" if concluidas == len(etapas) and etapas else "pendente",
            "etapas_concluidas": concluidas,
            "etapas_total": len(etapas),
            "pct": round((concluidas / len(etapas) * 100), 1) if etapas else 0,
        }
    except Exception as e:
        checks["seed"] = {"status": "erro", "detalhe": str(e)}

    # Fontes externas (paralelo, timeout curto)
    fontes_status = await _checar_fontes_externas()
    checks["fontes"] = fontes_status

    # Redis
    try:
        from config import get_settings
        import redis.asyncio as aredis
        settings = get_settings()
        r = aredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = {"status": "ok"}
    except Exception as e:
        checks["redis"] = {"status": "erro", "detalhe": str(e)}

    tempo_ms = int((time.time() - inicio) * 1000)
    status_geral = "ok" if checks["banco"].get("status") == "ok" else "degradado"

    return {
        "status": status_geral,
        "sistema": "VIGÍA",
        "versao": "1.0.0",
        "tempo_ms": tempo_ms,
        "checks": checks,
    }


async def _checar_fonte(nome: str, url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(url)
            return {
                "nome": nome,
                "status": "ok" if r.status_code < 400 else "erro",
                "http": r.status_code,
            }
    except Exception as e:
        return {"nome": nome, "status": "erro", "detalhe": str(e)[:50]}


async def _checar_fontes_externas() -> list[dict]:
    tasks = [_checar_fonte(nome, url) for nome, url in FONTES_EXTERNAS]
    return await asyncio.gather(*tasks)
