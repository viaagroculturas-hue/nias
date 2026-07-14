"""
Agente Fitossanitário — detecta risco de pragas e doenças.
Cruza condições climáticas com calendário de pragas por cultura.
"""
import logging
from datetime import datetime, timedelta, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.clima import AlertaClimatico, EventoClimatico
from models.pragas import PragaDoenca, OcorrenciaFitossanitaria
from models.safra import Safra
from models.geo import MunicipioSA

logger = logging.getLogger(__name__)

# Condições favoráveis a pragas críticas — cruzamento clima × cultura
REGRAS_PRAGA = [
    {
        "praga": "ferrugem_asiatica",
        "culturas": ["Soja"],
        "condicoes": {"umidade_min": 70, "temp_min": 18, "temp_max": 28},
        "janela_horas": 72,
        "perda_pct": 80,
        "nivel": "critico",
        "acao": "Aplicar fungicida sistêmico imediatamente (estrobilurina + triazol). Janela de 72h.",
    },
    {
        "praga": "brusone_trigo",
        "culturas": ["Trigo"],
        "condicoes": {"umidade_min": 80, "temp_min": 20, "temp_max": 30, "chuva_min": 10},
        "janela_horas": 48,
        "perda_pct": 70,
        "nivel": "critico",
        "acao": "Fungicida preventivo obrigatório. Avaliar seguro agrícola.",
    },
    {
        "praga": "lagarta_cartucho",
        "culturas": ["Milho"],
        "condicoes": {"temp_min": 22, "temp_max": 35, "umidade_max": 60},
        "janela_horas": 120,
        "perda_pct": 34,
        "nivel": "atencao",
        "acao": "Monitorar lavoura. Aplicar inseticida se infestação > 20% das plantas.",
    },
    {
        "praga": "mal_panama",
        "culturas": ["Banana"],
        "condicoes": {"temp_min": 24, "umidade_min": 75},
        "janela_horas": 0,
        "perda_pct": 100,
        "nivel": "critico",
        "acao": "DOENÇA SEM CURA. Isolar área, notificar MAPA/ADAGRI. Não mover material vegetal.",
    },
    {
        "praga": "requeima_tomate",
        "culturas": ["Tomate"],
        "condicoes": {"umidade_min": 85, "temp_min": 10, "temp_max": 25, "chuva_min": 5},
        "janela_horas": 36,
        "perda_pct": 90,
        "nivel": "critico",
        "acao": "Fungicida cúprico imediato. Reduzir molhamento foliar. Melhora drenagem.",
    },
    {
        "praga": "cigarrinha_cana",
        "culturas": ["Cana-de-açúcar"],
        "condicoes": {"umidade_min": 80, "temp_min": 22},
        "janela_horas": 168,
        "perda_pct": 25,
        "nivel": "atencao",
        "acao": "Monitorar infestação. Inseticida biológico (Beauveria bassiana) se nível de dano econômico.",
    },
    {
        "praga": "broca_cafe",
        "culturas": ["Café Arábica"],
        "condicoes": {"temp_min": 20, "temp_max": 30, "umidade_min": 60},
        "janela_horas": 336,
        "perda_pct": 35,
        "nivel": "atencao",
        "acao": "CBB traps. Colheita antecipada se infestação > 3%. Armadilhas Brocap.",
    },
]


class AgenteFitossanitario:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def executar(self) -> list[AlertaClimatico]:
        alertas = []

        # Buscar eventos climáticos recentes (últimas 48h)
        resultado = await self.db.execute(
            select(EventoClimatico)
            .where(EventoClimatico.created_at >= datetime.utcnow() - timedelta(hours=48))
            .limit(200)
        )
        eventos = resultado.scalars().all()

        # Buscar safras em andamento
        resultado2 = await self.db.execute(
            select(Safra).where(Safra.status.in_(["plantado", "vegetativo", "florescimento"]))
        )
        safras = resultado2.scalars().all()

        # Cruzar eventos × regras × safras
        for regra in REGRAS_PRAGA:
            for evento in eventos:
                if self._condicoes_favoraveis(evento, regra["condicoes"]):
                    dup = await self._alerta_duplicado(
                        f"praga_{regra['praga']}", evento.municipio_id
                    )
                    if dup:
                        continue

                    alerta = await self._criar_alerta_praga(regra, evento)
                    if alerta:
                        alertas.append(alerta)

        if alertas:
            await self.db.commit()
            logger.info(f"AgenteFitossanitario: {len(alertas)} alertas de pragas")

        return alertas

    def _condicoes_favoraveis(self, evento: EventoClimatico, cond: dict) -> bool:
        umidade = float(evento.umidade_pct or 0)
        temp_max = float(evento.temperatura_max or 25)
        temp_min = float(evento.temperatura_min or 15)
        precip = float(evento.precipitacao_mm or 0)

        if "umidade_min" in cond and umidade < cond["umidade_min"]:
            return False
        if "umidade_max" in cond and umidade > cond["umidade_max"]:
            return False
        if "temp_min" in cond and temp_max < cond["temp_min"]:
            return False
        if "temp_max" in cond and temp_min > cond["temp_max"]:
            return False
        if "chuva_min" in cond and precip < cond["chuva_min"]:
            return False
        return True

    async def _criar_alerta_praga(
        self, regra: dict, evento: EventoClimatico
    ) -> AlertaClimatico | None:
        janela = regra["janela_horas"]
        data_limite = (
            datetime.utcnow() + timedelta(hours=janela)
            if janela > 0 else None
        )

        alerta = AlertaClimatico(
            municipio_id=evento.municipio_id,
            tipo=f"praga_{regra['praga']}",
            nivel=regra["nivel"],
            titulo=f"Risco de {regra['praga'].replace('_', ' ').title()} — condições favoráveis",
            descricao=(
                f"Condições climáticas ideais para {regra['praga'].replace('_', ' ')}. "
                f"Culturas em risco: {', '.join(regra['culturas'])}. "
                f"Perda potencial: até {regra['perda_pct']}% da produção."
                + (f" Janela de ação: {janela}h." if janela > 0 else " Doença sem tratamento curativo.")
            ),
            acao_recomendada=regra["acao"],
            data_inicio=datetime.utcnow(),
            data_limite=data_limite,
            impacto_financeiro_estimado=self._estimar_impacto(regra["perda_pct"]),
            confianca_pct=75,
            fontes=["INMET", "VIGIA-fitossanitario"],
            status="ativo",
        )
        self.db.add(alerta)
        await self.db.flush()
        return alerta

    async def _alerta_duplicado(self, tipo: str, municipio_id) -> bool:
        result = await self.db.execute(
            select(AlertaClimatico).where(
                AlertaClimatico.tipo == tipo,
                AlertaClimatico.municipio_id == municipio_id,
                AlertaClimatico.status == "ativo",
                AlertaClimatico.created_at >= datetime.utcnow() - timedelta(hours=48),
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _estimar_impacto(self, perda_pct: float) -> float:
        area_media_ha = 50
        produtividade_t_ha = 3.5
        preco_t = 1500
        return round(area_media_ha * produtividade_t_ha * preco_t * perda_pct / 100, 2)
