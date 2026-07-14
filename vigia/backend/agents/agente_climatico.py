"""
Agente Climático — gera alertas a partir de dados INMET + NOAA.
Roda a cada 2h via verificacao_risco task.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.clima import AlertaClimatico, EventoClimatico, AlertaEnso
from models.geo import MunicipioSA
from services.inmet_service import get_condicao_ponto
from services.noaa_service import get_enso_completo
from services.verificacao_service import verificar_simples

logger = logging.getLogger(__name__)

# Limiares de alerta
CHUVA_ATENCAO  = 30   # mm
CHUVA_CRITICO  = 80   # mm
TEMP_CALOR     = 38   # °C
TEMP_GEADA     = 3    # °C
VENTO_ATENCAO  = 60   # km/h
VENTO_CRITICO  = 90   # km/h


class AgenteClimatico:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self) -> list[AlertaClimatico]:
        """Analisa dados climáticos e gera alertas."""
        alertas_gerados = []

        # 1. Alertas por dados INMET (municípios prioritários)
        municipios = await self._get_municipios_monitorados()
        for mun in municipios:
            try:
                alerta = await self._analisar_municipio(mun)
                if alerta:
                    alertas_gerados.append(alerta)
            except Exception as e:
                logger.debug(f"Climático {mun.nome}: {e}")

        # 2. Alerta ENSO se mudou de fase
        alerta_enso = await self._avaliar_enso()
        if alerta_enso:
            alertas_gerados.append(alerta_enso)

        if alertas_gerados:
            await self.db.commit()
            logger.info(f"AgenteClimatico: {len(alertas_gerados)} alertas gerados")

        return alertas_gerados

    async def _get_municipios_monitorados(self) -> list[MunicipioSA]:
        result = await self.db.execute(
            select(MunicipioSA)
            .where(
                MunicipioSA.lat.isnot(None),
                MunicipioSA.pais == "BRA",
            )
            .limit(50)
        )
        return result.scalars().all()

    async def _analisar_municipio(self, mun: MunicipioSA) -> AlertaClimatico | None:
        dados = await get_condicao_ponto(float(mun.lat), float(mun.lon))
        if not dados:
            return None

        nivel, tipo, titulo, descricao, acao = self._classificar(dados, mun.nome)
        if not nivel:
            return None

        # Verificar se já existe alerta ativo similar
        existente = await self._alerta_duplicado(mun.id, tipo)
        if existente:
            return None

        verif = verificar_simples(
            dados.get("precipitacao_mm") or dados.get("temp_max") or 0,
            [{"nome": "INMET", "valor": dados.get("precipitacao_mm", 0)}],
        )

        alerta = AlertaClimatico(
            municipio_id=mun.id,
            tipo=tipo,
            nivel=nivel,
            titulo=titulo,
            descricao=descricao,
            acao_recomendada=acao,
            data_inicio=datetime.utcnow(),
            data_limite=datetime.utcnow() + timedelta(hours=24),
            impacto_financeiro_estimado=self._estimar_impacto(nivel, mun),
            confianca_pct=verif["score_confianca"],
            fontes=["INMET"],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta

    def _classificar(
        self, dados: dict, nome: str
    ) -> tuple[str | None, str, str, str, str]:
        precip  = dados.get("precipitacao_mm") or 0
        tmax    = dados.get("temp_max") or 0
        tmin    = dados.get("temp_min") or 99
        vento   = dados.get("vento_km_h") or 0

        if precip >= CHUVA_CRITICO:
            return (
                "critico", "chuva_intensa",
                f"Chuva intensa em {nome}: {precip:.0f}mm",
                f"Precipitação de {precip:.0f}mm nas últimas horas. Risco de alagamento e erosão.",
                "Suspender operações de campo. Verificar drenos e terraços.",
            )
        if tmin <= TEMP_GEADA:
            return (
                "critico", "geada",
                f"Risco de geada em {nome}: {tmin:.1f}°C",
                f"Temperatura mínima de {tmin:.1f}°C. Culturas sensíveis em risco.",
                "Acionar irrigação noturna ou cobertura de proteção imediatamente.",
            )
        if tmax >= TEMP_CALOR:
            nivel = "critico" if tmax >= 40 else "atencao"
            return (
                nivel, "calor_extremo",
                f"Calor {'extremo' if nivel == 'critico' else 'intenso'} em {nome}: {tmax:.1f}°C",
                f"Temperatura máxima de {tmax:.1f}°C. Estresse hídrico e térmico nas culturas.",
                "Reforçar irrigação. Evitar aplicação de defensivos no calor do dia.",
            )
        if vento >= VENTO_CRITICO:
            return (
                "critico", "vento_forte",
                f"Ventos fortes em {nome}: {vento:.0f}km/h",
                f"Rajadas de {vento:.0f}km/h. Risco de acamamento e queda de frutos.",
                "Suspender pulverizações aéreas. Proteger estufas e estruturas.",
            )
        if precip >= CHUVA_ATENCAO:
            return (
                "atencao", "chuva_moderada",
                f"Chuva moderada em {nome}: {precip:.0f}mm",
                f"Precipitação de {precip:.0f}mm. Monitorar drenagem.",
                "Monitorar acúmulo de água. Atrasar operações leves.",
            )
        return (None, "", "", "", "")

    async def _alerta_duplicado(self, municipio_id, tipo: str) -> bool:
        result = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.municipio_id == municipio_id,
                AlertaClimatico.tipo == tipo,
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(hours=6),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _estimar_impacto(self, nivel: str, mun: MunicipioSA) -> float:
        base = {"info": 10_000, "atencao": 50_000, "critico": 200_000}
        return float(base.get(nivel, 0))

    async def _avaliar_enso(self) -> AlertaClimatico | None:
        enso = await get_enso_completo()
        if not enso.get("disponivel"):
            return None
        if enso.get("nivel_alerta") not in ("atencao", "critico"):
            return None

        tipo_enso = enso.get("tipo_enso", "neutro")
        oni       = enso.get("oni_index", 0)

        # Não duplicar alerta ENSO recente
        result = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.tipo == f"enso_{tipo_enso}",
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(days=7),
            ).limit(1)
        )
        if result.scalar_one_or_none():
            return None

        regioes = enso.get("impacto_regional", {})
        culturas_risco = regioes.get("culturas_risco", [])

        alerta = AlertaClimatico(
            tipo=f"enso_{tipo_enso}",
            nivel=enso["nivel_alerta"],
            titulo=f"ENSO: {tipo_enso.replace('_', ' ').title()} detectado — ONI {oni:+.1f}",
            descricao=(
                f"Índice ONI de {oni:+.1f} confirma {tipo_enso.replace('_', ' ')}. "
                f"Impacto regional: {regioes.get('risco_principal', 'monitorar')}. "
                f"Culturas em risco: {', '.join(culturas_risco[:3])}."
            ),
            acao_recomendada="; ".join(enso.get("recomendacoes", [])[:2]),
            data_inicio=datetime.utcnow(),
            data_limite=datetime.utcnow() + timedelta(days=90),
            confianca_pct=enso.get("prob_el_nino") or enso.get("prob_la_nina") or 60,
            fontes=["NOAA-CPC"],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta
