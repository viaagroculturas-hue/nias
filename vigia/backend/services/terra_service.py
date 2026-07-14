from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.clima import AlertaClimatico
from models.inteligencia import GritoTerra, AuditoriaVigia
from services.notificacao_service import NotificacaoService
import logging

logger = logging.getLogger(__name__)

CRITERIOS_TERRA = {
    "confianca_minima_pct": 85,
    "impacto_financeiro_minimo": 100_000,
    "janela_acao_maxima_horas": 48,
    "fontes_minimas": 2,
    "nivel_alerta": "critico",
}


class TerraService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.notificacao = NotificacaoService()

    async def verificar_e_ativar(self) -> list[dict]:
        """Varre todos os alertas críticos ativos e dispara TERRA nos elegíveis."""
        result = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.nivel == "critico",
                AlertaClimatico.status == "ativo",
            )
        )
        alertas = result.scalars().all()

        terras = []
        for alerta in alertas:
            terra = await self.avaliar_e_disparar(alerta)
            if terra:
                terras.append({
                    "id": str(terra.id),
                    "cultura": terra.cultura,
                    "situacao": terra.situacao,
                    "risco": terra.risco,
                    "janela_horas": terra.janela_horas,
                    "acao_exata": terra.acao_exata,
                    "patrimonio_em_risco": float(terra.patrimonio_em_risco or 0),
                    "confianca_pct": terra.confianca_pct,
                    "fontes": terra.fontes or [],
                })
        return terras

    async def avaliar_e_disparar(self, alerta: AlertaClimatico) -> GritoTerra | None:
        if not self._atende_criterios(alerta):
            return None

        terra = await self._criar_grito_terra(alerta)
        await self.db.commit()

        await self._disparar_websocket_terra(terra)
        await self.notificacao.enviar_terra(terra)
        await self._registrar_auditoria(terra)

        logger.critical(f"TERRA disparado: {terra.cultura} · {terra.situacao[:60]}")
        return terra

    def _atende_criterios(self, alerta: AlertaClimatico) -> bool:
        if alerta.nivel != CRITERIOS_TERRA["nivel_alerta"]:
            return False
        if (alerta.confianca_pct or 0) < CRITERIOS_TERRA["confianca_minima_pct"]:
            return False
        if (alerta.impacto_financeiro_estimado or 0) < CRITERIOS_TERRA["impacto_financeiro_minimo"]:
            return False
        fontes = alerta.fontes or []
        if len(fontes) < CRITERIOS_TERRA["fontes_minimas"]:
            return False
        return True

    async def _criar_grito_terra(self, alerta: AlertaClimatico) -> GritoTerra:
        terra = GritoTerra(
            alerta_id=alerta.id,
            municipio_id=alerta.municipio_id,
            cultura=alerta.tipo,
            situacao=alerta.descricao or "",
            risco=alerta.titulo or "",
            janela_horas=int(
                (alerta.data_limite - datetime.utcnow()).total_seconds() / 3600
            ) if alerta.data_limite else 24,
            acao_exata=alerta.acao_recomendada or "Contatar agrônomo imediatamente",
            impacto_financeiro=alerta.impacto_financeiro_estimado,
            confianca_pct=alerta.confianca_pct,
            fontes=alerta.fontes,
            patrimonio_em_risco=alerta.impacto_financeiro_estimado,
            notificados=[],
        )
        self.db.add(terra)
        await self.db.flush()
        return terra

    async def _disparar_websocket_terra(self, terra: GritoTerra):
        try:
            from routers.radar import broadcast_terra
            await broadcast_terra({
                "id": str(terra.id),
                "cultura": terra.cultura,
                "situacao": terra.situacao,
                "risco": terra.risco,
                "janela_horas": terra.janela_horas,
                "acao_exata": terra.acao_exata,
                "patrimonio_em_risco": float(terra.patrimonio_em_risco or 0),
                "confianca_pct": terra.confianca_pct,
                "fontes": terra.fontes or [],
            })
        except Exception as e:
            logger.error(f"WebSocket TERRA falhou: {e}")

    async def _registrar_auditoria(self, terra: GritoTerra):
        audit = AuditoriaVigia(
            entidade="grito_terra",
            entidade_id=terra.id,
            acao="disparado",
            dados_novos={
                "situacao": terra.situacao,
                "janela_horas": terra.janela_horas,
                "patrimonio": float(terra.patrimonio_em_risco or 0),
            },
            agente="terra_service",
        )
        self.db.add(audit)

    def _montar_mensagem_terra(self, terra: GritoTerra) -> str:
        return (
            f"TERRA.\n\n"
            f"{terra.cultura} · municipio\n\n"
            f"{terra.situacao}\n\n"
            f"Risco: {terra.risco}\n"
            f"Janela: {terra.janela_horas}h\n"
            f"Impacto estimado: R$ {float(terra.patrimonio_em_risco or 0):,.0f}\n"
            f"Ação: {terra.acao_exata}\n\n"
            f"Confiança: {terra.confianca_pct}%\n"
            f"Fontes: {', '.join(str(f) for f in (terra.fontes or []))}"
        )
