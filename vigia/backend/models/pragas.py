from sqlalchemy import Column, String, Numeric, ForeignKey, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.sql import func


class PragaDoenca(Base):
    __tablename__ = "praga_doenca"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome_comum = Column(String(200))
    nome_cientifico = Column(String(200))
    tipo = Column(String(50))
    culturas_afetadas = Column(JSONB)
    condicoes_favoraveis = Column(JSONB)
    sintomas = Column(String)
    tratamentos = Column(JSONB)
    perda_potencial_pct = Column(Numeric(5, 2))
    janela_acao_horas = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    ocorrencias = relationship("OcorrenciaFitossanitaria", back_populates="praga_doenca")


class OcorrenciaFitossanitaria(Base):
    __tablename__ = "ocorrencia_fitossanitaria"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    talhao_id = Column(UUID(as_uuid=True), ForeignKey("talhao.id"))
    safra_id = Column(UUID(as_uuid=True), ForeignKey("safra.id"))
    praga_doenca_id = Column(UUID(as_uuid=True), ForeignKey("praga_doenca.id"))
    nivel_risco = Column(String(20))
    data_deteccao = Column(TIMESTAMP(timezone=True))
    area_afetada_pct = Column(Numeric(5, 2))
    fonte_deteccao = Column(String(100))
    acao_recomendada = Column(String)
    data_resolucao = Column(TIMESTAMP(timezone=True))
    resultado = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    talhao = relationship("Talhao", back_populates="ocorrencias")
    safra = relationship("Safra", back_populates="ocorrencias")
    praga_doenca = relationship("PragaDoenca", back_populates="ocorrencias")
