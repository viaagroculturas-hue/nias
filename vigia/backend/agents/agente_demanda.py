"""
Agente de Demanda — monitora fatores que afetam consumo de alimentos.
Fontes: GLP-1, câmbio, eventos climáticos globais, exportações.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.clima import AlertaClimatico
from models.inteligencia import FatorDemanda, EventoDemanda

logger = logging.getLogger(__name__)


class AgenteDemanda:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self) -> list[AlertaClimatico]:
        alertas = []

        fatores = await self._get_fatores_ativos()
        for fator in fatores:
            alerta = await self._avaliar_fator(fator)
            if alerta:
                alertas.append(alerta)

        if alertas:
            await self.db.commit()
            logger.info(f"AgenteDemanda: {len(alertas)} alertas de demanda")

        return alertas

    async def _get_fatores_ativos(self) -> list[FatorDemanda]:
        result = await self.db.execute(
            select(FatorDemanda).where(FatorDemanda.ativo == True)
        )
        return result.scalars().all()

    async def _avaliar_fator(self, fator: FatorDemanda) -> AlertaClimatico | None:
        # Verificar se alerta recente já existe
        dup = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.tipo == f"demanda_{fator.slug}",
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(days=30),
            ).limit(1)
        )
        if dup.scalar_one_or_none():
            return None

        # Só gera alerta se impacto relevante
        if abs(fator.impacto_volume_pct or 0) < 3:
            return None

        direcao = "queda" if (fator.impacto_volume_pct or 0) < 0 else "alta"
        nivel = "critico" if abs(fator.impacto_volume_pct or 0) >= 10 else "atencao"

        alerta = AlertaClimatico(
            tipo=f"demanda_{fator.slug}",
            nivel=nivel,
            titulo=f"Demanda: {fator.nome} — {direcao} de {abs(fator.impacto_volume_pct or 0):.0f}%",
            descricao=(
                f"{fator.descricao}. "
                f"Impacto estimado: {fator.impacto_volume_pct:+.1f}% no volume. "
                f"Culturas afetadas: {', '.join((fator.culturas_afetadas or [])[:3])}. "
                f"Fonte: {fator.fonte}."
            ),
            acao_recomendada=fator.acao_recomendada or "Monitorar evolução do indicador.",
            data_inicio=datetime.utcnow(),
            data_limite=datetime.utcnow() + timedelta(days=90),
            confianca_pct=fator.confianca_pct or 70,
            fontes=[fator.fonte],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta
