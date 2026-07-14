"""
Agente de Produção — previsões de safra e desvios de estimativa.
Usa dados CONAB + clima + NDVI para ajustar projeções.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.clima import AlertaClimatico
from models.safra import ProjecaoSafra, Safra

logger = logging.getLogger(__name__)

DESVIO_ATENCAO = 10.0   # % abaixo da estimativa inicial
DESVIO_CRITICO = 20.0   # %


class AgenteProducao:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self) -> list[AlertaClimatico]:
        alertas = []

        projecoes = await self._get_projecoes_ativas()
        for proj in projecoes:
            alerta = await self._avaliar_projecao(proj)
            if alerta:
                alertas.append(alerta)

        if alertas:
            await self.db.commit()
            logger.info(f"AgenteProducao: {len(alertas)} alertas de produção")

        return alertas

    async def _get_projecoes_ativas(self) -> list[ProjecaoSafra]:
        result = await self.db.execute(
            select(ProjecaoSafra)
            .where(ProjecaoSafra.safra_ano >= datetime.utcnow().year)
            .limit(50)
        )
        return result.scalars().all()

    async def _avaliar_projecao(self, proj: ProjecaoSafra) -> AlertaClimatico | None:
        if not proj.producao_estimada_t or not proj.producao_revisada_t:
            return None

        desvio = (
            (proj.producao_revisada_t - proj.producao_estimada_t)
            / proj.producao_estimada_t * 100
        )

        if desvio >= 0 or abs(desvio) < DESVIO_ATENCAO:
            return None

        nivel = "critico" if abs(desvio) >= DESVIO_CRITICO else "atencao"

        dup = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.tipo == f"producao_{proj.id}",
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(days=14),
            ).limit(1)
        )
        if dup.scalar_one_or_none():
            return None

        alerta = AlertaClimatico(
            tipo=f"producao_{proj.id}",
            nivel=nivel,
            titulo=(
                f"Revisão de safra {proj.cultura} {proj.safra_ano}: "
                f"queda de {abs(desvio):.1f}%"
            ),
            descricao=(
                f"Estimativa inicial: {proj.producao_estimada_t:,.0f}t. "
                f"Revisão atual: {proj.producao_revisada_t:,.0f}t ({desvio:+.1f}%). "
                f"Motivo: {proj.motivo_revisao or 'Condições climáticas adversas'}."
            ),
            acao_recomendada=(
                "Revisar contratos de venda futura. "
                "Avaliar cobertura de seguro. "
                "Reforçar monitoramento das lavouras restantes."
            ),
            data_inicio=datetime.utcnow(),
            data_limite=datetime.utcnow() + timedelta(days=30),
            impacto_financeiro_estimado=abs(
                (proj.producao_estimada_t - proj.producao_revisada_t) * 1500
            ),
            confianca_pct=80,
            fontes=["CONAB", "VIGIA-producao"],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta
