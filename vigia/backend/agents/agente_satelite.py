"""
Agente Satélite — processa NDVI e detecta anomalias de vegetação.
Gera alertas quando NDVI desvia do padrão esperado para a fase da cultura.
"""
import logging
import statistics
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.clima import AlertaClimatico
from models.satelite import MapeamentoSatelite
from models.geo import MunicipioSA
from services.gee_service import calcular_ndvi_municipio

logger = logging.getLogger(__name__)

# NDVI esperado por fase da cultura (referência soja/milho)
NDVI_ESPERADO = {
    "plantio_emergencia":  (0.15, 0.30),
    "vegetativo_inicial":  (0.30, 0.55),
    "vegetativo_pleno":    (0.55, 0.75),
    "florescimento":       (0.65, 0.80),
    "granacao":            (0.55, 0.75),
    "maturacao":           (0.30, 0.55),
    "solo_exposto":        (0.05, 0.15),
}

ZSCORE_ALERTA = 2.0
NDVI_QUEDA_BRUSCA = -0.15   # queda de 0.15 em 10 dias → alerta


class AgenteSatelite:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self, municipios: list[MunicipioSA] = None) -> list[AlertaClimatico]:
        alertas = []

        if municipios is None:
            resultado = await self.db.execute(
                select(MunicipioSA)
                .where(MunicipioSA.lat.isnot(None))
                .limit(30)
            )
            municipios = resultado.scalars().all()

        for mun in municipios:
            try:
                ndvi_novo = calcular_ndvi_municipio(float(mun.lat), float(mun.lon))
                if not ndvi_novo:
                    continue

                # Salvar mapeamento
                mapeamento = MapeamentoSatelite(
                    municipio_id=mun.id,
                    ndvi_medio=ndvi_novo["ndvi_medio"],
                    fase_estimada=ndvi_novo["fase_estimada"],
                    data_imagem=date.today(),
                    satelite=ndvi_novo["satelite"],
                    confianca_pct=85 if not ndvi_novo.get("simulado") else 40,
                )

                # Detectar anomalia vs histórico
                historico = await self._get_historico_ndvi(mun.id)
                anomalia = self._detectar_anomalia(
                    ndvi_novo["ndvi_medio"], historico
                )

                mapeamento.anomalia_detectada = anomalia["detectada"]
                mapeamento.z_score = anomalia.get("z_score")
                self.db.add(mapeamento)

                if anomalia["detectada"]:
                    alerta = await self._criar_alerta_ndvi(mun, ndvi_novo, anomalia)
                    if alerta:
                        alertas.append(alerta)

            except Exception as e:
                logger.debug(f"Satélite {mun.nome}: {e}")

        if alertas:
            await self.db.commit()
            logger.info(f"AgenteSatelite: {len(alertas)} anomalias detectadas")

        return alertas

    async def _get_historico_ndvi(self, municipio_id) -> list[float]:
        resultado = await self.db.execute(
            select(MapeamentoSatelite.ndvi_medio)
            .where(MapeamentoSatelite.municipio_id == municipio_id)
            .order_by(MapeamentoSatelite.data_imagem.desc())
            .limit(20)
        )
        return [float(r[0]) for r in resultado.fetchall() if r[0] is not None]

    def _detectar_anomalia(self, ndvi: float, historico: list[float]) -> dict:
        if len(historico) < 5:
            return {"detectada": False}

        media = statistics.mean(historico)
        desvio = statistics.stdev(historico)
        if desvio == 0:
            return {"detectada": False}

        z = (ndvi - media) / desvio

        # Queda brusca em relação ao último
        queda = ndvi - historico[0] if historico else 0

        return {
            "detectada": abs(z) >= ZSCORE_ALERTA or queda <= NDVI_QUEDA_BRUSCA,
            "z_score": round(z, 3),
            "queda_brusca": queda <= NDVI_QUEDA_BRUSCA,
            "media_historica": round(media, 4),
            "ndvi_atual": ndvi,
        }

    async def _criar_alerta_ndvi(
        self, mun: MunicipioSA, ndvi_dados: dict, anomalia: dict
    ) -> AlertaClimatico | None:
        # Verificar duplicata
        resultado = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.tipo == "ndvi_anomalia",
                AlertaClimatico.municipio_id == mun.id,
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(days=5),
            ).limit(1)
        )
        if resultado.scalar_one_or_none():
            return None

        ndvi = ndvi_dados["ndvi_medio"]
        media = anomalia.get("media_historica", 0)
        z = anomalia.get("z_score", 0)
        queda = anomalia.get("queda_brusca", False)

        if queda:
            titulo = f"Queda brusca de NDVI em {mun.nome} — possível estresse"
            descricao = (
                f"NDVI caiu de {media:.3f} para {ndvi:.3f} nos últimos 10 dias. "
                f"Possíveis causas: seca, praga, geada ou colheita antecipada. "
                f"Fase detectada: {ndvi_dados['fase_estimada']}."
            )
            nivel = "critico" if (media - ndvi) > 0.25 else "atencao"
        else:
            direcao = "abaixo" if z < 0 else "acima"
            titulo = f"NDVI {direcao} do padrão em {mun.nome} ({abs(z):.1f}σ)"
            descricao = (
                f"NDVI atual {ndvi:.3f} vs média histórica {media:.3f} "
                f"({abs(z):.1f} desvios padrão {direcao}). "
                f"Satélite: {ndvi_dados['satelite']}. Fase: {ndvi_dados['fase_estimada']}."
            )
            nivel = "critico" if abs(z) >= 3.0 else "atencao"

        alerta = AlertaClimatico(
            municipio_id=mun.id,
            tipo="ndvi_anomalia",
            nivel=nivel,
            titulo=titulo,
            descricao=descricao,
            acao_recomendada="Visita de campo para confirmar causa. Verificar dados INMET locais.",
            data_inicio=datetime.utcnow(),
            data_limite=datetime.utcnow() + timedelta(days=7),
            confianca_pct=75 if not ndvi_dados.get("simulado") else 40,
            fontes=[ndvi_dados["satelite"], "VIGIA-satelite"],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta
