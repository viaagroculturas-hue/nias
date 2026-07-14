from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, TIMESTAMP, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from database import Base
import uuid
from sqlalchemy.sql import func


class Cultura(Base):
    __tablename__ = "cultura"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(100), nullable=False)
    nome_cientifico = Column(String(200))
    categoria = Column(String(50))   # graos | hortifruti | frutas | commodities | andinas
    subcategoria = Column(String(50))
    ciclo_dias_min = Column(Integer)
    ciclo_dias_max = Column(Integer)
    ndvi_fases = Column(JSONB)        # assinatura espectral por fase
    temp_ideal_min = Column(Numeric(4, 1))
    temp_ideal_max = Column(Numeric(4, 1))
    chuva_ciclo_min_mm = Column(Integer)
    chuva_ciclo_max_mm = Column(Integer)
    pragas_principais = Column(JSONB)
    paises_producao = Column(JSONB)
    preco_referencia_fonte = Column(String(100))
    unidade = Column(String(20))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    calendarios = relationship("CalendarioAgricola", back_populates="cultura")
    safras = relationship("Safra", back_populates="cultura")
    cotacoes = relationship("CotacaoProduto", back_populates="cultura")
    producoes_muda = relationship("ProducaoMuda", back_populates="cultura")


class CalendarioAgricola(Base):
    __tablename__ = "calendario_agricola"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cultura_id = Column(UUID(as_uuid=True), ForeignKey("cultura.id"))
    pais = Column(String(3))
    estado = Column(String(2))
    regiao = Column(String(100))
    meses_plantio = Column(ARRAY(Integer))
    meses_colheita = Column(ARRAY(Integer))
    sistema = Column(String(50))     # irrigado | sequeiro | estufa
    altitude_min_m = Column(Integer)
    altitude_max_m = Column(Integer)
    observacoes = Column(String)
    fonte = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    cultura = relationship("Cultura", back_populates="calendarios")
