"""
Agente Territorial — análise geoespacial de risco por município/região.
Detecta concentração de alertas (cluster) e escalona para nível regional.
"""
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.clima import AlertaClimatico
from models.geo import MunicipioSA

logger = logging.getLogger(__name__)

CLUSTER_MINIMO = 5       # municípios com alerta para virar alerta regional
RAIO_CLUSTER_KM = 200    # raio para considerar cluster


class AgenteTermitorial:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self) -> list[AlertaClimatico]:
        alertas = []

        # Detectar clusters de alertas críticos
        clusters = await self._detectar_clusters()
        for cluster in clusters:
            alerta = await self._criar_alerta_regional(cluster)
            if alerta:
                alertas.append(alerta)

        if alertas:
            await self.db.commit()
            logger.info(f"AgenteTerritorial: {len(alertas)} alertas regionais")

        return alertas

    async def _detectar_clusters(self) -> list[dict]:
        """Agrupa alertas críticos por estado/UF."""
        resultado = await self.db.execute(
            select(
                MunicipioSA.uf,
                MunicipioSA.pais,
                func.count(AlertaClimatico.id).label("total_alertas"),
                func.sum(AlertaClimatico.impacto_financeiro_estimado).label("impacto_total"),
            )
            .join(AlertaClimatico, AlertaClimatico.municipio_id == MunicipioSA.id)
            .where(
                AlertaClimatico.nivel == "critico",
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(hours=24),
            )
            .group_by(MunicipioSA.uf, MunicipioSA.pais)
            .having(func.count(AlertaClimatico.id) >= CLUSTER_MINIMO)
        )

        clusters = []
        for row in resultado.fetchall():
            clusters.append({
                "uf": row.uf,
                "pais": row.pais,
                "total_alertas": row.total_alertas,
                "impacto_total": float(row.impacto_total or 0),
            })

        return clusters

    async def _criar_alerta_regional(self, cluster: dict) -> AlertaClimatico | None:
        chave = f"regional_{cluster['pais']}_{cluster['uf'] or 'nacional'}"

        dup = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.tipo == chave,
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(hours=12),
            ).limit(1)
        )
        if dup.scalar_one_or_none():
            return None

        uf_label = cluster["uf"] or "região"
        impacto = cluster["impacto_total"]
        n = cluster["total_alertas"]

        alerta = AlertaClimatico(
            tipo=chave,
            nivel="critico",
            titulo=f"Cluster de alertas: {n} municípios em {uf_label} ({cluster['pais']})",
            descricao=(
                f"{n} municípios com alertas críticos simultâneos em {uf_label}. "
                f"Impacto financeiro agregado estimado: R$ {impacto:,.0f}. "
                f"Possível evento climático de escala regional."
            ),
            acao_recomendada=(
                "Acionar defesa civil estadual. "
                "Contatar secretaria de agricultura. "
                "Ativar canais de comunicação com produtores da região."
            ),
            data_inicio=datetime.utcnow(),
            data_limite=datetime.utcnow() + timedelta(hours=72),
            impacto_financeiro_estimado=impacto,
            confianca_pct=90,
            fontes=["VIGIA-territorial"],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta
