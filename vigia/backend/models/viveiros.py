from sqlalchemy import Column, String, Numeric, ForeignKey, TIMESTAMP, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.sql import func


class Viveiro(Base):
    __tablename__ = "viveiro"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    municipio_id = Column(UUID(as_uuid=True), ForeignKey("municipio_sa.id"))
    nome = Column(String(255))
    numero_renasem = Column(String(50))
    culturas_produzidas = Column(JSONB)
    capacidade_mudas_mes = Column(Integer)
    sistemas = Column(JSONB)
    lat = Column(Numeric(10, 7))
    lon = Column(Numeric(10, 7))
    status = Column(String(50), default="ativo")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    municipio = relationship("MunicipioSA", back_populates="viveiros")
    producoes = relationship("ProducaoMuda", back_populates="viveiro")


class ProducaoMuda(Base):
    __tablename__ = "producao_muda"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    viveiro_id = Column(UUID(as_uuid=True), ForeignKey("viveiro.id"))
    cultura_id = Column(UUID(as_uuid=True), ForeignKey("cultura.id"))
    mes_producao = Column(TIMESTAMP(timezone=True))
    volume_mudas = Column(Integer)
    demanda_nivel = Column(String(50))   # baixa | normal | alta | critica
    sinal_mercado = Column(String)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    viveiro = relationship("Viveiro", back_populates="producoes")
    cultura = relationship("Cultura", back_populates="producoes_muda")
