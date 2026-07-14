from sqlalchemy import Column, String, Numeric, ForeignKey, TIMESTAMP, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.sql import func


class CotacaoProduto(Base):
    __tablename__ = "cotacao_produto"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cultura_id = Column(UUID(as_uuid=True), ForeignKey("cultura.id"))
    praca = Column(String(255))
    pais = Column(String(3))
    preco = Column(Numeric(12, 2))
    unidade = Column(String(20))
    data_cotacao = Column(Date)
    variacao_pct = Column(Numeric(6, 2))
    tendencia = Column(String(20))
    fonte = Column(String(100))
    confianca_pct = Column(Numeric(5, 2))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    cultura = relationship("Cultura", back_populates="cotacoes")


class RotaLogistica(Base):
    __tablename__ = "rota_logistica"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    origem = Column(String(255))
    destino = Column(String(255))
    tipo = Column(String(50))    # rodoviario | maritimo | ferroviario
    distancia_km = Column(Numeric(8, 1))
    frete_por_tonelada = Column(Numeric(10, 2))
    tempo_transito_h = Column(Numeric(6, 1))
    capacidade_t = Column(Numeric(8, 1))
    disponibilidade_data = Column(Date)
    status = Column(String(50))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
