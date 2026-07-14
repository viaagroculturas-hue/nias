import asyncio
import json
import logging
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db, AsyncSessionLocal
from models.inteligencia import SeedStatus
from tasks.seed_autonomo import ETAPAS_SEED, executar_seed

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_seed_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SeedStatus).order_by(SeedStatus.etapa))
    etapas = result.scalars().all()

    if not etapas:
        return {
            "iniciado": False,
            "etapas": [],
            "pct_total": 0,
            "concluido": False,
        }

    concluidas = sum(1 for e in etapas if e.status == "concluido")
    com_erro = sum(1 for e in etapas if e.status == "erro")
    total = len(etapas)

    return {
        "iniciado": True,
        "etapas": [
            {
                "etapa": e.etapa,
                "nome": e.nome,
                "status": e.status,
                "pct_concluido": float(e.pct_concluido or 0),
                "registros_processados": e.registros_processados or 0,
                "registros_total": e.registros_total or 0,
                "iniciado_em": e.iniciado_em.isoformat() if e.iniciado_em else None,
                "concluido_em": e.concluido_em.isoformat() if e.concluido_em else None,
                "erro": e.erro,
            }
            for e in etapas
        ],
        "pct_total": round((concluidas / total) * 100, 1) if total else 0,
        "concluido": concluidas == total and total == len(ETAPAS_SEED),
        "com_erro": com_erro,
        "etapas_previstas": [
            {"etapa": e["etapa"], "nome": e["nome"], "duracao_estimada_min": e["duracao_estimada_min"]}
            for e in ETAPAS_SEED
        ],
    }


@router.get("/stream")
async def stream_seed_status():
    """
    SSE — Server-Sent Events para progresso do seed em tempo real.
    O frontend conecta uma vez e recebe atualizações sem polling.
    """
    async def gerar():
        ultima_versao = None
        tentativas_sem_mudanca = 0

        while True:
            try:
                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(SeedStatus).order_by(SeedStatus.etapa)
                    )
                    etapas = result.scalars().all()

                if not etapas:
                    payload = json.dumps({"iniciado": False, "pct_total": 0})
                else:
                    concluidas = sum(1 for e in etapas if e.status == "concluido")
                    total = len(ETAPAS_SEED)
                    payload = json.dumps({
                        "iniciado": True,
                        "pct_total": round((concluidas / total) * 100, 1) if total else 0,
                        "concluido": concluidas == total,
                        "etapas": [
                            {
                                "etapa": e.etapa,
                                "nome": e.nome,
                                "status": e.status,
                                "pct_concluido": float(e.pct_concluido or 0),
                                "registros_processados": e.registros_processados or 0,
                                "registros_total": e.registros_total or 0,
                            }
                            for e in etapas
                        ],
                    })

                # Só emite se houve mudança (evita spam)
                if payload != ultima_versao:
                    ultima_versao = payload
                    tentativas_sem_mudanca = 0
                    yield f"data: {payload}\n\n"
                else:
                    tentativas_sem_mudanca += 1

                # Se concluído há 3 ciclos → encerrar stream
                try:
                    dados = json.loads(payload)
                    if dados.get("concluido") and tentativas_sem_mudanca >= 3:
                        yield f"data: {json.dumps({'concluido': True, 'encerrar': True})}\n\n"
                        break
                except Exception:
                    pass

                await asyncio.sleep(2)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"SSE seed stream erro: {e}")
                yield f"data: {json.dumps({'erro': str(e)})}\n\n"
                await asyncio.sleep(5)

    return StreamingResponse(
        gerar(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/iniciar")
async def iniciar_seed(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SeedStatus).where(SeedStatus.status == "concluido").limit(1)
    )
    ja_rodou = result.scalar_one_or_none()
    if ja_rodou:
        return {"message": "Seed já foi executado anteriormente", "status": "skip"}

    result2 = await db.execute(
        select(SeedStatus).where(SeedStatus.status == "rodando").limit(1)
    )
    ja_rodando = result2.scalar_one_or_none()
    if ja_rodando:
        return {"message": "Seed em andamento", "status": "rodando"}

    background_tasks.add_task(executar_seed)
    return {"message": "Seed iniciado", "status": "iniciado"}


@router.post("/resetar")
async def resetar_seed(db: AsyncSession = Depends(get_db)):
    """Dev only — resetar seed para novo boot. Remover em produção."""
    from sqlalchemy import delete
    await db.execute(delete(SeedStatus))
    await db.commit()
    return {"message": "Seed resetado — próximo boot executará novamente"}
