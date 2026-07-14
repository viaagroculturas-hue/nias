from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from database import Base
import uuid
from sqlalchemy.sql import func


class MunicipioSA(Base):
    __tablename__ = "municipio_sa"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome = Column(String(255), nullable=False)
    codigo_ibge = Column(String(10))
    estado = Column(String(2))
    pais = Column(String(3), nullable=False)
    lat = Column(Numeric(10, 7))
    lon = Column(Numeric(10, 7))
    geom = Column(Geometry("POINT", srid=4326))
    populacao = Column(Integer)
    area_territorial_km2 = Column(Numeric(12, 2))
    regiao_agricola = Column(String(100))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    propriedades = relationship("Propriedade", back_populates="municipio")
    alertas = relationship("AlertaClimatico", back_populates="municipio")
    eventos_climaticos = relationship("EventoClimatico", back_populates="municipio")
    previsoes_climaticas = relationship("PrevisaoClimatica", back_populates="municipio")
    mapeamentos = relationship("MapeamentoSatelite", back_populates="municipio")
    viveiros = relationship("Viveiro", back_populates="municipio")


class Propriedade(Base):
    __tablename__ = "propriedade"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    municipio_id = Column(UUID(as_uuid=True), ForeignKey("municipio_sa.id"))
    nome = Column(String(255), nullable=False)
    lat = Column(Numeric(10, 7))
    lon = Column(Numeric(10, 7))
    area_total_ha = Column(Numeric(10, 2))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    municipio = relationship("MunicipioSA", back_populates="propriedades")
    talhoes = relationship("Talhao", back_populates="propriedade")


class Talhao(Base):
    __tablename__ = "talhao"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    propriedade_id = Column(UUID(as_uuid=True), ForeignKey("propriedade.id"))
    nome = Column(String(100))
    area_ha = Column(Numeric(8, 2))
    lat = Column(Numeric(10, 7))
    lon = Column(Numeric(10, 7))
    geom = Column(Geometry("POLYGON", srid=4326))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    propriedade = relationship("Propriedade", back_populates="talhoes")
    safras = relationship("Safra", back_populates="talhao")
    alertas = relationship("AlertaClimatico", back_populates="talhao")
    ocorrencias = relationship("OcorrenciaFitossanitaria", back_populates="talhao")
    tarefas = relationship("TarefaOperacional", back_populates="talhao")
    recomendacoes = relationship("RecomendacaoVigia", back_populates="talhao")
    mapeamentos = relationship("MapeamentoSatelite", back_populates="municipio", overlaps="municipio,mapeamentos")
