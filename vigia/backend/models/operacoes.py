from sqlalchemy import Column, String, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.sql import func


class TarefaOperacional(Base):
    __tablename__ = "tarefa_operacional"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    talhao_id = Column(UUID(as_uuid=True), ForeignKey("talhao.id"))
    safra_id = Column(UUID(as_uuid=True), ForeignKey("safra.id"))
    alerta_id = Column(UUID(as_uuid=True), ForeignKey("alerta_climatico.id"))
    tipo = Column(String(100))
    titulo = Column(String(255), nullable=False)
    descricao = Column(String)
    data_prazo = Column(TIMESTAMP(timezone=True), nullable=False)
    data_execucao = Column(TIMESTAMP(timezone=True))
    responsavel = Column(String(255), nullable=False)
    custo_estimado = Column(Numeric(12, 2))
    custo_real = Column(Numeric(12, 2))
    status = Column(String(50), default="pendente")
    prioridade = Column(String(20), default="normal")
    resultado = Column(String)
    origem = Column(String(100))   # manual | vigia_automatico | alerta
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    talhao = relationship("Talhao", back_populates="tarefas")
    safra = relationship("Safra", back_populates="tarefas")
    alerta = relationship("AlertaClimatico", back_populates="tarefas")
    recomendacao = relationship("RecomendacaoVigia", back_populates="tarefa_gerada",
                                foreign_keys="RecomendacaoVigia.tarefa_gerada_id")
