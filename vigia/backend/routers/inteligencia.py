from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.inteligencia import RecomendacaoVigia, GritoTerra
from models.clima import AlertaClimatico
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/recomendacoes")
async def get_recomendacoes(status: str = "pendente", limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RecomendacaoVigia)
        .where(RecomendacaoVigia.status == status)
        .order_by(RecomendacaoVigia.prazo_acao)
        .limit(limit)
    )
    return [
        {
            "id": str(r.id),
            "tipo": r.tipo,
            "titulo": r.titulo,
            "descricao": r.descricao,
            "justificativa": r.justificativa,
            "impacto_financeiro_estimado": float(r.impacto_financeiro_estimado) if r.impacto_financeiro_estimado else None,
            "confianca_pct": float(r.confianca_pct) if r.confianca_pct else None,
            "nivel_urgencia": r.nivel_urgencia,
            "prazo_acao": r.prazo_acao.isoformat() if r.prazo_acao else None,
        }
        for r in result.scalars().all()
    ]


@router.post("/agentes/executar")
async def executar_agentes(db: AsyncSession = Depends(get_db)):
    """Trigger manual do ciclo de agentes — usado em dev/debug."""
    try:
        from agents import executar_todos_agentes
        resultado = await executar_todos_agentes(db)
        return {"status": "ok", "resultado": resultado}
    except Exception as e:
        logger.error(f"Trigger agentes erro: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notificacao/teste")
async def teste_notificacao():
    """Envia mensagem de teste para todos os destinatários configurados."""
    from services.notificacao_service import NotificacaoService, _destinos_whatsapp
    destinos = _destinos_whatsapp()
    if not destinos:
        return {"status": "sem_destinos", "message": "Configure NOTIFICACAO_DESTINOS_WHATSAPP no .env"}

    svc = NotificacaoService()
    # Usa um objeto fake com a interface mínima esperada
    class FakeRelatorio:
        data_referencia = None
        alertas_criticos = []
        oportunidades = []
        acoes_do_dia = [{"titulo": "Teste VIGÍA"}]

    ok = await svc.enviar_whatsapp_resumo(FakeRelatorio())
    return {"status": "enviado" if ok else "falhou", "destinos": len(destinos)}


@router.get("/terra/historico")
async def get_terra_historico(limit: int = 20, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(GritoTerra).order_by(GritoTerra.disparado_em.desc()).limit(limit)
    )
    return [
        {
            "id": str(t.id),
            "cultura": t.cultura,
            "situacao": t.situacao,
            "janela_horas": t.janela_horas,
            "patrimonio_em_risco": float(t.patrimonio_em_risco) if t.patrimonio_em_risco else None,
            "resolvido": t.resolvido,
            "disparado_em": t.disparado_em.isoformat() if t.disparado_em else None,
        }
        for t in result.scalars().all()
    ]
