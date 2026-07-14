"""
Relatório das 05h30 — antes do mercado abrir.
Antes do sol nascer. O VIGÍA já trabalhou a noite inteira.
"""
import asyncio
from datetime import date
from celery import shared_task
from database import AsyncSessionLocal
from sqlalchemy import select, func
from models.clima import AlertaClimatico
from models.inteligencia import RelatórioManha, CotacaoProduto, AlertaEnso
from services.claude_service import gerar_resumo_executivo
from services.notificacao_service import NotificacaoService
import logging

logger = logging.getLogger(__name__)

FONTES_CONSULTADAS_HOJE = [
    "INMET", "CEPEA", "CONAB", "IBGE", "BCB", "NOAA-CPC",
    "CPTEC/INPE", "SMN-ARG", "DMC-Chile", "SENAMHI-Peru",
]


@shared_task(name="tasks.relatorio_manha.gerar_relatorio_manha")
def gerar_relatorio_manha():
    asyncio.get_event_loop().run_until_complete(_gerar())


async def _gerar():
    async with AsyncSessionLocal() as db:
        hoje = date.today()

        alertas_criticos = await _get_alertas(db, "critico")
        alertas_atencao = await _get_alertas(db, "atencao")
        oportunidades = await _get_oportunidades(db)
        mercado_snapshot = await _get_cotacoes(db)
        enso_snapshot = await _get_enso(db)

        resumo = await gerar_resumo_executivo(
            alertas=alertas_criticos + alertas_atencao,
            mercado=mercado_snapshot,
            clima={},
            enso=enso_snapshot,
        )

        acoes_do_dia = _gerar_3_acoes(alertas_criticos, oportunidades)

        relatorio = RelatórioManha(
            data_referencia=hoje,
            resumo_executivo=resumo,
            alertas_criticos=[_serializar_alerta(a) for a in alertas_criticos],
            alertas_atencao=[_serializar_alerta(a) for a in alertas_atencao],
            oportunidades=oportunidades,
            mercado_snapshot=mercado_snapshot,
            enso_snapshot=enso_snapshot,
            acoes_do_dia=acoes_do_dia,
            municipios_monitorados=await _count_municipios(db),
            alertas_gerados=len(alertas_criticos) + len(alertas_atencao),
            fontes_consultadas=FONTES_CONSULTADAS_HOJE,
        )
        db.add(relatorio)
        await db.flush()

        notif = NotificacaoService()
        try:
            ok = await notif.enviar_whatsapp_resumo(relatorio)
            relatorio.enviado_whatsapp = ok
        except Exception as e:
            logger.error(f"WhatsApp 05h30 erro: {e}")

        await db.commit()
        logger.info(f"Relatório {hoje} gerado — {len(alertas_criticos)} críticos")


async def _get_alertas(db, nivel: str) -> list:
    result = await db.execute(
        select(AlertaClimatico)
        .where(AlertaClimatico.nivel == nivel, AlertaClimatico.status == "ativo")
        .order_by(AlertaClimatico.created_at.desc())
        .limit(20)
    )
    return result.scalars().all()


async def _get_oportunidades(db) -> list:
    return []  # implementar: alertas de oportunidade


async def _get_cotacoes(db) -> dict:
    from models.mercado import CotacaoProduto
    result = await db.execute(
        select(CotacaoProduto)
        .order_by(CotacaoProduto.data_cotacao.desc())
        .limit(10)
    )
    cotacoes = result.scalars().all()
    return [{"praca": c.praca, "preco": float(c.preco or 0), "variacao": float(c.variacao_pct or 0)}
            for c in cotacoes]


async def _get_enso(db) -> dict:
    result = await db.execute(
        select(AlertaEnso).order_by(AlertaEnso.created_at.desc()).limit(1)
    )
    enso = result.scalar_one_or_none()
    if not enso:
        return {}
    return {
        "tipo": enso.tipo_enso,
        "oni": float(enso.oni_index or 0),
        "probabilidade": float(enso.probabilidade_pct or 0),
        "nivel": enso.nivel_alerta,
    }


async def _count_municipios(db) -> int:
    from models.geo import MunicipioSA
    result = await db.execute(select(func.count(MunicipioSA.id)))
    return result.scalar() or 0


def _gerar_3_acoes(alertas_criticos: list, oportunidades: list) -> list:
    acoes = []
    for alerta in alertas_criticos[:3]:
        acoes.append({
            "titulo": alerta.titulo or "Verificar alerta crítico",
            "acao": alerta.acao_recomendada or "Consultar agrônomo",
            "prazo": str(alerta.data_limite) if alerta.data_limite else "hoje",
            "origem": "alerta_critico",
        })
    while len(acoes) < 3:
        acoes.append({
            "titulo": "Monitorar previsão climática",
            "acao": "Verificar painel de clima no VIGÍA",
            "prazo": "hoje",
            "origem": "rotina",
        })
    return acoes[:3]


def _serializar_alerta(a: AlertaClimatico) -> dict:
    return {
        "id": str(a.id),
        "tipo": a.tipo,
        "nivel": a.nivel,
        "titulo": a.titulo,
        "descricao": a.descricao,
        "acao_recomendada": a.acao_recomendada,
        "confianca_pct": float(a.confianca_pct or 0),
        "impacto": float(a.impacto_financeiro_estimado or 0),
    }
