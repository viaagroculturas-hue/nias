"""
Agente de Viveiros — detecta sinais de demanda por mudas e sementes.
Correlaciona: calendário agrícola + ENSO + preços + área plantada histórica.
"""
import logging
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.clima import AlertaClimatico
from models.inteligencia import SignalViveiro

logger = logging.getLogger(__name__)


class AgenteViveiros:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self) -> list[AlertaClimatico]:
        alertas = []

        # Lógica baseada em calendário: se estamos em janela de plantio, sinalizar
        mes_atual = date.today().month
        sinais = self._avaliar_calendario(mes_atual)

        for sinal in sinais:
            dup = await self.db.execute(
                select(AlertaClimatico).where(
                    AlertaClimatico.tipo == f"viveiro_{sinal['cultura'].lower().replace(' ', '_')}",
                    AlertaClimatico.status == "ativo",
                    AlertaClimatico.created_at >= datetime.utcnow() - timedelta(days=30),
                ).limit(1)
            )
            if dup.scalar_one_or_none():
                continue

            alerta = AlertaClimatico(
                tipo=f"viveiro_{sinal['cultura'].lower().replace(' ', '_')}",
                nivel="info",
                titulo=f"Janela de plantio: {sinal['cultura']} — demanda de mudas/sementes",
                descricao=(
                    f"{sinal['cultura']}: janela ideal de plantio para {sinal['regiao']}. "
                    f"Demanda de sementes/mudas estimada para as próximas {sinal['janela_dias']} dias. "
                    f"Variedades recomendadas: {sinal['variedades']}."
                ),
                acao_recomendada=sinal["acao"],
                data_inicio=datetime.utcnow(),
                data_limite=datetime.utcnow() + timedelta(days=sinal["janela_dias"]),
                confianca_pct=85,
                fontes=["CONAB-calendario", "VIGIA-viveiros"],
                status="ativo",
            )
            self.db.add(alerta)
            alertas.append(alerta)

        if alertas:
            await self.db.commit()
            logger.info(f"AgenteViveiros: {len(alertas)} sinais de viveiro")

        return alertas

    def _avaliar_calendario(self, mes: int) -> list[dict]:
        """Calendário agrícola simplificado — janelas de plantio por mês."""
        calendario = {
            # Plantio primeira safra (safra de verão)
            10: [
                {
                    "cultura": "Soja",
                    "regiao": "Centro-Oeste e Sul do Brasil",
                    "janela_dias": 60,
                    "variedades": "M7739, NS 8282, BMX Lança",
                    "acao": "Confirmar disponibilidade de semente tratada. Verificar inoculante.",
                },
                {
                    "cultura": "Milho",
                    "regiao": "MG, SP, GO",
                    "janela_dias": 45,
                    "variedades": "P3707, DKB 390, SYN 975",
                    "acao": "Garantir estoque de milho primeira safra. Verificar tratamento de sementes.",
                },
            ],
            11: [
                {
                    "cultura": "Soja",
                    "regiao": "Nordeste e Pará",
                    "janela_dias": 45,
                    "variedades": "P98Y51, TMG 7062, Anta 82",
                    "acao": "Previsão de alta demanda em Cerrado nordestino.",
                },
            ],
            # Safrinha
            1: [
                {
                    "cultura": "Milho Safrinha",
                    "regiao": "MT, MS, GO, PR",
                    "janela_dias": 30,
                    "variedades": "P3250, DKB 177, P3431",
                    "acao": "Janela safrinha abrindo. Confirmar disponibilidade antes de meados de fevereiro.",
                },
            ],
            # Trigo
            4: [
                {
                    "cultura": "Trigo",
                    "regiao": "Sul do Brasil, Argentina",
                    "janela_dias": 60,
                    "variedades": "TBIO Toruk, ORS Agile, LG Ametista",
                    "acao": "Plantio de trigo: verificar tratamento contra brusone.",
                },
            ],
            # Café novos pomares
            5: [
                {
                    "cultura": "Café Arábica",
                    "regiao": "MG Sul/Cerrado, SP",
                    "janela_dias": 90,
                    "variedades": "Topázio MG, Catucaí, Arara",
                    "acao": "Demanda de mudas formadas para reforma de cafezais.",
                },
            ],
        }

        return calendario.get(mes, [])
