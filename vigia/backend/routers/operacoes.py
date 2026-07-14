from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models.operacoes import TarefaOperacional

router = APIRouter()


@router.get("/tarefas")
async def get_tarefas(status: str = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    q = select(TarefaOperacional).order_by(TarefaOperacional.data_prazo)
    if status:
        q = q.where(TarefaOperacional.status == status)
    result = await db.execute(q.limit(limit))
    return [
        {
            "id": str(t.id),
            "titulo": t.titulo,
            "tipo": t.tipo,
            "responsavel": t.responsavel,
            "status": t.status,
            "prioridade": t.prioridade,
            "data_prazo": t.data_prazo.isoformat() if t.data_prazo else None,
            "origem": t.origem,
            "custo_estimado": float(t.custo_estimado) if t.custo_estimado else None,
        }
        for t in result.scalars().all()
    ]
