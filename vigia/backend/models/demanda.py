from sqlalchemy import Column, String, Numeric, ForeignKey, TIMESTAMP, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from database import Base
import uuid
from sqlalchemy.sql import func


class FatorDemanda(Base):
    __tablename__ = "fator_demanda"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255))
    tipo = Column(String(100))
    impacto_direcao = Column(String(10))  # reducao | aumento
    impacto_pct = Column(Numeric(6, 2))
    culturas_afetadas = Column(JSONB)
    paises_afetados = Column(JSONB)
    classes_renda_afetadas = Column(JSONB)
    periodo_inicio = Column(Date)
    periodo_fim = Column(Date)
    fonte_dado = Column(String)
    url_fonte = Column(String)
    confianca_pct = Column(Numeric(5, 2))
    ativo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class EventoCalendario(Base):
    __tablename__ = "evento_calendario"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255))
    tipo = Column(String(100))   # feriado | esporte | festival | cultural | sanitario
    pais = Column(String(3))
    estado = Column(String(2))
    data_inicio = Column(Date)
    data_fim = Column(Date)
    impacto_alimentar = Column(JSONB)
    culturas_afetadas = Column(JSONB)
    direcao = Column(String(10))   # aumento | reducao | neutro
    magnitude = Column(String(20))
    fonte = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
