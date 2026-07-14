"""
Agente de Mercado — detecta movimentos de preço e oportunidades.
Analisa CEPEA, câmbio BCB e tendências.
"""
import logging
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models.clima import AlertaClimatico
from models.mercado import CotacaoProduto
from services.cepea_service import get_todas_cotacoes
from services.bcb_service import get_cambio_atual, get_serie_historica
from services.verificacao_service import verificar_simples

logger = logging.getLogger(__name__)

VARIACAO_ATENCAO  = 5.0   # %
VARIACAO_CRITICA  = 10.0  # %
CAMBIO_ALTO       = 5.50  # USD/BRL


class AgenteMercado:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self) -> list[AlertaClimatico]:
        alertas = []

        # 1. Coletar cotações CEPEA e analisar
        cotacoes = await get_todas_cotacoes()
        for cot in cotacoes:
            alerta = await self._analisar_cotacao(cot)
            if alerta:
                alertas.append(alerta)

        # 2. Analisar câmbio
        alerta_cambio = await self._analisar_cambio()
        if alerta_cambio:
            alertas.append(alerta_cambio)

        # 3. Detectar divergência histórica (preço muito acima/abaixo da média)
        alertas_hist = await self._analisar_historico()
        alertas.extend(alertas_hist)

        if alertas:
            await self.db.commit()
            logger.info(f"AgenteMercado: {len(alertas)} alertas gerados")

        return alertas

    async def _analisar_cotacao(self, cot: dict) -> AlertaClimatico | None:
        variacao = cot.get("variacao_pct") or 0
        if abs(variacao) < VARIACAO_ATENCAO:
            return None

        nivel = "critico" if abs(variacao) >= VARIACAO_CRITICA else "atencao"
        direcao = "alta" if variacao > 0 else "queda"
        emoji_dir = "▲" if variacao > 0 else "▼"

        # Verificar duplicata
        dup = await self._alerta_duplicado(f"mercado_{cot['slug']}")
        if dup:
            return None

        alerta = AlertaClimatico(
            tipo=f"mercado_{cot['slug']}",
            nivel=nivel,
            titulo=f"{emoji_dir} {cot['produto']}: {direcao} de {abs(variacao):.1f}%",
            descricao=(
                f"{cot['produto']} em {cot['praca']}: R$ {cot['preco']:.2f}/{cot['unidade']} "
                f"({'+' if variacao > 0 else ''}{variacao:.1f}% em relação ao dia anterior). "
                f"Fonte: CEPEA/ESALQ."
            ),
            acao_recomendada=(
                f"{'Avaliar antecipação de venda' if variacao > 0 else 'Aguardar recuperação antes de vender'}. "
                f"Verificar contratos futuros B3."
            ),
            data_inicio=datetime.utcnow(),
            data_limite=datetime.utcnow() + timedelta(hours=48),
            impacto_financeiro_estimado=self._estimar_impacto_mercado(cot["preco"], variacao),
            confianca_pct=90,
            fontes=["CEPEA-ESALQ"],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta

    async def _analisar_cambio(self) -> AlertaClimatico | None:
        cambio = await get_cambio_atual()
        usd = cambio.get("usd_brl")
        if not usd:
            return None

        if usd < CAMBIO_ALTO:
            return None

        dup = await self._alerta_duplicado("cambio_alto")
        if dup:
            return None

        alerta = AlertaClimatico(
            tipo="cambio_alto",
            nivel="atencao",
            titulo=f"USD/BRL elevado: R$ {usd:.3f} — oportunidade de exportação",
            descricao=(
                f"Dólar em R$ {usd:.3f} favorece exportadores de commodities. "
                f"Soja, milho e café ficam mais competitivos no mercado externo. "
                f"Importados (fertilizantes, defensivos) ficam mais caros."
            ),
            acao_recomendada=(
                "Avaliar contratos de exportação. "
                "Revisar custo de insumos importados para safra próxima."
            ),
            data_inicio=datetime.utcnow(),
            data_limite=datetime.utcnow() + timedelta(days=7),
            confianca_pct=99,
            fontes=["BCB-SGS"],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta

    async def _analisar_historico(self) -> list[AlertaClimatico]:
        """Detecta preços muito fora da média histórica (90 dias)."""
        alertas = []
        hoje = date.today()
        noventa_dias = hoje - timedelta(days=90)

        result = await self.db.execute(
            select(
                CotacaoProduto.praca,
                func.avg(CotacaoProduto.preco).label("media"),
                func.stddev(CotacaoProduto.preco).label("desvio"),
                func.max(CotacaoProduto.preco).label("ultimo"),
            )
            .where(CotacaoProduto.data_cotacao >= noventa_dias)
            .group_by(CotacaoProduto.praca)
            .having(func.count(CotacaoProduto.id) >= 10)
        )

        for row in result.fetchall():
            if not row.desvio or row.desvio == 0:
                continue
            z = (row.ultimo - row.media) / row.desvio
            if abs(z) < 2.5:
                continue

            dup = await self._alerta_duplicado(f"preco_anomalia_{row.praca[:20]}")
            if dup:
                continue

            direcao = "acima" if z > 0 else "abaixo"
            alerta = AlertaClimatico(
                tipo=f"preco_anomalia_{row.praca[:20]}",
                nivel="atencao",
                titulo=f"Preço {direcao} da média histórica: {row.praca}",
                descricao=(
                    f"Cotação atual {abs(z):.1f} desvios-padrão {direcao} da média de 90 dias. "
                    f"Média: R$ {row.media:.2f} | Atual: R$ {row.ultimo:.2f}"
                ),
                acao_recomendada="Verificar fundamentos. Comparar com safra atual e ENSO.",
                data_inicio=datetime.utcnow(),
                data_limite=datetime.utcnow() + timedelta(days=3),
                confianca_pct=80,
                fontes=["CEPEA-ESALQ", "VIGIA-historico"],
                status="ativo",
            )
            self.db.add(alerta)
            await self.db.flush()
            alertas.append(alerta)

        return alertas

    async def _alerta_duplicado(self, tipo: str) -> bool:
        result = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.tipo == tipo,
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(hours=12),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _estimar_impacto_mercado(self, preco: float, variacao_pct: float) -> float:
        producao_media_t = 500
        impacto = producao_media_t * preco * abs(variacao_pct) / 100
        return round(impacto, 2)
