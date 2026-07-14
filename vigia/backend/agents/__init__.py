"""
Orquestrador de agentes VIGÍA.
Todos os agentes são instanciados com a mesma sessão de DB para consistência transacional.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from agents.agente_climatico import AgenteClimatico
from agents.agente_satelite import AgenteSatelite
from agents.agente_fitossanitario import AgenteFitossanitario
from agents.agente_mercado import AgenteMercado
from agents.agente_demanda import AgenteDemanda
from agents.agente_producao import AgenteProducao
from agents.agente_viveiros import AgenteViveiros
from agents.agente_territorial import AgenteTermitorial
from agents.agente_aprendizado import AgenteAprendizado

logger = logging.getLogger(__name__)


async def executar_todos_agentes(db: AsyncSession) -> dict:
    """
    Roda todos os agentes em sequência.
    Territorial roda por último (precisa dos alertas gerados pelos outros).
    Aprendizado roda ao final para calcular métricas.
    """
    resultados = {}

    agentes_primarios = [
        ("climatico",      AgenteClimatico(db)),
        ("satelite",       AgenteSatelite(db)),
        ("fitossanitario", AgenteFitossanitario(db)),
        ("mercado",        AgenteMercado(db)),
        ("demanda",        AgenteDemanda(db)),
        ("producao",       AgenteProducao(db)),
        ("viveiros",       AgenteViveiros(db)),
    ]

    total_alertas = 0
    for nome, agente in agentes_primarios:
        try:
            alertas = await agente.executar()
            resultados[nome] = len(alertas)
            total_alertas += len(alertas)
        except Exception as e:
            logger.error(f"Agente {nome} falhou: {e}", exc_info=True)
            resultados[nome] = 0

    # Territorial: escala alertas em cluster
    try:
        alertas_regional = await AgenteTermitorial(db).executar()
        resultados["territorial"] = len(alertas_regional)
        total_alertas += len(alertas_regional)
    except Exception as e:
        logger.error(f"Agente territorial falhou: {e}", exc_info=True)
        resultados["territorial"] = 0

    # Verificar TERRA em todos os alertas críticos gerados
    from services.terra_service import TerraService
    from routers.radar import broadcast_terra
    try:
        terra_svc = TerraService(db)
        terras = await terra_svc.verificar_e_ativar()
        for terra in terras:
            await broadcast_terra(terra)
        resultados["terra_ativados"] = len(terras)
    except Exception as e:
        logger.error(f"TerraService falhou: {e}", exc_info=True)
        resultados["terra_ativados"] = 0

    # Aprendizado: roda semanalmente (segunda-feira)
    from datetime import datetime
    if datetime.utcnow().weekday() == 0:
        try:
            metricas = await AgenteAprendizado(db).executar()
            resultados["aprendizado"] = len(metricas)
        except Exception as e:
            logger.error(f"Agente aprendizado falhou: {e}", exc_info=True)

    logger.info(
        f"Ciclo agentes concluído: {total_alertas} alertas | "
        f"TERRA: {resultados.get('terra_ativados', 0)}"
    )
    return resultados
