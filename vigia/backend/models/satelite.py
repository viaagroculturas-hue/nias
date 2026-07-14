from sqlalchemy import Column, String, Numeric, ForeignKey, TIMESTAMP, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from database import Base
import uuid
from sqlalchemy.sql import func


class MapeamentoSatelite(Base):
    __tablename__ = "mapeamento_satelite"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    municipio_id = Column(UUID(as_uuid=True), ForeignKey("municipio_sa.id"))
    cultura_detectada = Column(String(100))
    area_ha = Column(Numeric(12, 2))
    confianca_pct = Column(Numeric(5, 2))
    ndvi_medio = Column(Numeric(6, 4))
    fase_estimada = Column(String(50))
    data_imagem = Column(Date)
    satelite = Column(String(50))
    geom = Column(Geometry("MULTIPOLYGON", srid=4326))
    status_producao = Column(String(50))
    anomalia_detectada = Column(Boolean, default=False)
    z_score = Column(Numeric(6, 3))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    municipio = relationship("MunicipioSA", back_populates="mapeamentos")
