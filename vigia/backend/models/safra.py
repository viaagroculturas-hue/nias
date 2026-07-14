from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, TIMESTAMP, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.sql import func


class Safra(Base):
    __tablename__ = "safra"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    talhao_id = Column(UUID(as_uuid=True), ForeignKey("talhao.id"))
    cultura_id = Column(UUID(as_uuid=True), ForeignKey("cultura.id"))
    ano_safra = Column(String(7))
    data_plantio = Column(Date)
    data_colheita_prevista = Column(Date)
    data_colheita_real = Column(Date)
    area_plantada_ha = Column(Numeric(8, 2))
    produtividade_esperada_t_ha = Column(Numeric(8, 3))
    produtividade_real_t_ha = Column(Numeric(8, 3))
    custo_estimado_ha = Column(Numeric(10, 2))
    custo_real_ha = Column(Numeric(10, 2))
    receita_total = Column(Numeric(14, 2))
    margem_liquida = Column(Numeric(14, 2))
    status = Column(String(50), default="planejado")
    fase_atual = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    talhao = relationship("Talhao", back_populates="safras")
    cultura = relationship("Cultura", back_populates="safras")
    previsoes = relationship("PrevisaoSafra", back_populates="safra")
    alertas = relationship("AlertaClimatico", back_populates="safra")
    ocorrencias = relationship("OcorrenciaFitossanitaria", back_populates="safra")
    tarefas = relationship("TarefaOperacional", back_populates="safra")
    recomendacoes = relationship("RecomendacaoVigia", back_populates="safra")


class PrevisaoSafra(Base):
    __tablename__ = "previsao_safra"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    safra_id = Column(UUID(as_uuid=True), ForeignKey("safra.id"))
    data_previsao = Column(TIMESTAMP(timezone=True), server_default=func.now())
    producao_prevista_t = Column(Numeric(10, 3))
    data_colheita_estimada = Column(Date)
    confianca_pct = Column(Numeric(5, 2))
    metodo = Column(String(100))
    ndvi_atual = Column(Numeric(6, 4))
    fontes = Column(JSONB)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    safra = relationship("Safra", back_populates="previsoes")
