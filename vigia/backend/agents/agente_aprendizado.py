"""
Agente de Aprendizado — feedback loop de precisão.
Verifica alertas passados e recalcula taxa de acerto por tipo/fonte.
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from models.clima import AlertaClimatico
from models.inteligencia import MetricaAgente

logger = logging.getLogger(__name__)


class AgenteAprendizado:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self) -> dict:
        """Calcula métricas de precisão e ajusta pesos de confiança."""
        metricas = {}

        tipos = await self._get_tipos_alertas()
        for tipo in tipos:
            metrica = await self._calcular_precisao(tipo)
            if metrica:
                metricas[tipo] = metrica
                await self._salvar_metrica(tipo, metrica)

        await self.db.commit()
        logger.info(f"AgenteAprendizado: {len(metricas)} tipos analisados")
        return metricas

    async def _get_tipos_alertas(self) -> list[str]:
        result = await self.db.execute(
            select(AlertaClimatico.tipo)
            .where(AlertaClimatico.created_at >= datetime.utcnow() - timedelta(days=90))
            .distinct()
        )
        return [r[0] for r in result.fetchall()]

    async def _calcular_precisao(self, tipo: str) -> dict | None:
        # Alertas que tiveram feedback (resolvido ou falso_positivo)
        result = await self.db.execute(
            select(
                func.count(AlertaClimatico.id).label("total"),
                func.sum(
                    func.cast(AlertaClimatico.confirmado == True, func.Integer)
                ).label("confirmados"),
            ).where(
                AlertaClimatico.tipo == tipo,
                AlertaClimatico.status.in_(["resolvido", "falso_positivo"]),
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(days=90),
            )
        )
        row = result.fetchone()
        if not row or not row.total or row.total < 5:
            return None

        taxa = float(row.confirmados or 0) / float(row.total)

        return {
            "tipo": tipo,
            "total_alertas": row.total,
            "confirmados": row.confirmados or 0,
            "taxa_acerto": round(taxa * 100, 1),
            "periodo_dias": 90,
        }

    async def _salvar_metrica(self, tipo: str, metrica: dict):
        # Upsert via check-then-insert
        result = await self.db.execute(
            select(MetricaAgente).where(MetricaAgente.tipo_alerta == tipo).limit(1)
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.taxa_acerto_pct = metrica["taxa_acerto"]
            existing.total_alertas = metrica["total_alertas"]
            existing.updated_at = datetime.utcnow()
        else:
            self.db.add(MetricaAgente(
                tipo_alerta=tipo,
                taxa_acerto_pct=metrica["taxa_acerto"],
                total_alertas=metrica["total_alertas"],
            ))
