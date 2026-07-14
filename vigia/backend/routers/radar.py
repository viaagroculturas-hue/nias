from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database import get_db
from models.clima import AlertaClimatico
from models.inteligencia import RelatórioManha, GritoTerra
from models.mercado import CotacaoProduto
from datetime import date
import json
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

_ws_clients: list[WebSocket] = []


@router.get("/")
async def get_radar(db: AsyncSession = Depends(get_db)):
    """Radar Vivo — visão consolidada do momento."""
    alertas_criticos = await _count_nivel(db, "critico")
    alertas_atencao = await _count_nivel(db, "atencao")
    terra_ativo = await _terra_ativo(db)
    relatorio_hoje = await _relatorio_hoje(db)

    return {
        "alertas": {
            "critico": alertas_criticos,
            "atencao": alertas_atencao,
            "info": await _count_nivel(db, "info"),
        },
        "terra_ativo": terra_ativo,
        "relatorio_hoje": relatorio_hoje,
        "ultima_atualizacao": date.today().isoformat(),
    }


@router.get("/alertas")
async def get_alertas(
    nivel: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    q = select(AlertaClimatico).where(AlertaClimatico.status == "ativo")
    if nivel:
        q = q.where(AlertaClimatico.nivel == nivel)
    q = q.order_by(AlertaClimatico.created_at.desc()).limit(limit)
    result = await db.execute(q)
    alertas = result.scalars().all()

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
            "fontes": a.fontes,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alertas
    ]


@router.websocket("/ws")
async def websocket_radar(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        _ws_clients.remove(websocket)


async def broadcast_terra(terra_data: dict):
    """Chamado pelo TerraService para notificar todos os clientes."""
    payload = json.dumps({"type": "TERRA", "data": terra_data})
    for ws in _ws_clients.copy():
        try:
            await ws.send_text(payload)
        except Exception:
            _ws_clients.discard(ws)


async def _count_nivel(db: AsyncSession, nivel: str) -> int:
    result = await db.execute(
        select(func.count(AlertaClimatico.id))
        .where(AlertaClimatico.nivel == nivel, AlertaClimatico.status == "ativo")
    )
    return result.scalar() or 0


async def _terra_ativo(db: AsyncSession) -> dict | None:
    result = await db.execute(
        select(GritoTerra)
        .where(GritoTerra.resolvido == False)
        .order_by(GritoTerra.disparado_em.desc())
        .limit(1)
    )
    terra = result.scalar_one_or_none()
    if not terra:
        return None
    return {
        "id": str(terra.id),
        "cultura": terra.cultura,
        "situacao": terra.situacao,
        "risco": terra.risco,
        "janela_horas": terra.janela_horas,
        "acao_exata": terra.acao_exata,
        "patrimonio_em_risco": float(terra.patrimonio_em_risco or 0),
        "confianca_pct": float(terra.confianca_pct or 0),
        "disparado_em": terra.disparado_em.isoformat() if terra.disparado_em else None,
    }


async def _relatorio_hoje(db: AsyncSession) -> dict | None:
    result = await db.execute(
        select(RelatórioManha)
        .where(RelatórioManha.data_referencia == date.today())
        .order_by(RelatórioManha.gerado_em.desc())
        .limit(1)
    )
    r = result.scalar_one_or_none()
    if not r:
        return None
    return {
        "resumo_executivo": r.resumo_executivo,
        "alertas_criticos": len(r.alertas_criticos or []),
        "acoes_do_dia": r.acoes_do_dia,
        "gerado_em": r.gerado_em.isoformat() if r.gerado_em else None,
    }
