from sqlalchemy import Column, String, Numeric, ForeignKey, TIMESTAMP, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.sql import func


class EventoClimatico(Base):
    __tablename__ = "evento_climatico"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    municipio_id = Column(UUID(as_uuid=True), ForeignKey("municipio_sa.id"))
    tipo = Column(String(100))
    data_inicio = Column(TIMESTAMP(timezone=True))
    data_fim = Column(TIMESTAMP(timezone=True))
    intensidade = Column(String(50))
    precipitacao_mm = Column(Numeric(8, 2))
    temperatura_min = Column(Numeric(5, 2))
    temperatura_max = Column(Numeric(5, 2))
    umidade_pct = Column(Numeric(5, 2))
    vento_km_h = Column(Numeric(6, 2))
    fonte = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    municipio = relationship("MunicipioSA", back_populates="eventos_climaticos")


class AlertaClimatico(Base):
    __tablename__ = "alerta_climatico"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    talhao_id = Column(UUID(as_uuid=True), ForeignKey("talhao.id"))
    safra_id = Column(UUID(as_uuid=True), ForeignKey("safra.id"))
    municipio_id = Column(UUID(as_uuid=True), ForeignKey("municipio_sa.id"))
    tipo = Column(String(100))
    nivel = Column(String(20))   # info | atencao | critico | terra
    titulo = Column(String(255))
    descricao = Column(String)
    data_inicio = Column(TIMESTAMP(timezone=True))
    data_limite = Column(TIMESTAMP(timezone=True))
    acao_recomendada = Column(String)
    impacto_financeiro_estimado = Column(Numeric(14, 2))
    confianca_pct = Column(Numeric(5, 2))
    fontes = Column(JSONB)
    status = Column(String(50), default="ativo")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    talhao = relationship("Talhao", back_populates="alertas")
    safra = relationship("Safra", back_populates="alertas")
    municipio = relationship("MunicipioSA", back_populates="alertas")
    tarefas = relationship("TarefaOperacional", back_populates="alerta")
    grito_terra = relationship("GritoTerra", back_populates="alerta")


class PrevisaoClimatica(Base):
    __tablename__ = "previsao_climatica"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    municipio_id = Column(UUID(as_uuid=True), ForeignKey("municipio_sa.id"))
    periodo_inicio = Column(Date)
    periodo_fim = Column(Date)
    tipo = Column(String(50))    # curto_prazo | sazonal | enso
    precipitacao_anomalia_pct = Column(Numeric(8, 2))
    temperatura_anomalia_c = Column(Numeric(5, 2))
    prob_el_nino = Column(Numeric(5, 2))
    prob_la_nina = Column(Numeric(5, 2))
    prob_neutro = Column(Numeric(5, 2))
    confianca_pct = Column(Numeric(5, 2))
    impacto_culturas = Column(JSONB)
    fonte = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    municipio = relationship("MunicipioSA", back_populates="previsoes_climaticas")


class AlertaEnso(Base):
    __tablename__ = "alerta_enso"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo_enso = Column(String(20))
    oni_index = Column(Numeric(5, 2))
    probabilidade_pct = Column(Numeric(5, 2))
    periodo_previsto = Column(String(50))
    regioes_impactadas = Column(JSONB)
    culturas_em_risco = Column(JSONB)
    culturas_beneficiadas = Column(JSONB)
    recomendacoes = Column(JSONB)
    nivel_alerta = Column(String(20))
    valido_ate = Column(Date)
    fonte = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
