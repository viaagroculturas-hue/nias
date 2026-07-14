"""
Verificação de veracidade — nenhum dado entra no VIGÍA sem passar por aqui.
Triangulação multi-fonte, score de confiança, detecção de anomalia.
"""
import hashlib
import json
import statistics
import logging
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.inteligencia import DadoVerificado

logger = logging.getLogger(__name__)

# n_fontes_independentes → (score_confianca, status, bloqueado)
ESCALA_CONFIANCA = {
    0: (0,   "SEM_FONTE",   True),
    1: (60,  "PRELIMINAR",  False),
    2: (80,  "CONFIRMADO",  False),
    3: (95,  "VERIFICADO",  False),
}

DIVERGENCIA_MAXIMA_PCT = 15.0   # acima disso → flag revisão humana
ZSCORE_ANOMALIA = 3.0           # desvios padrão para considerar anomalia


class VerificacaoService:
    """Nenhum dado entra no VIGÍA sem passar por aqui."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def verificar(
        self,
        valor: float,
        fontes: list[dict],
        campo: str = "",
        entidade_id: str = None,
        salvar: bool = True,
    ) -> dict:
        """
        Parâmetros de fontes esperados:
          {"nome": "CEPEA", "url": "...", "valor": 123.45, "coletado_em": "...", "hash_raw": "..."}
        """
        independentes = self._filtrar_independentes(fontes)
        n = min(len(independentes), 3)
        confianca, status, bloqueado = ESCALA_CONFIANCA[n]

        historico = await self._get_historico(campo)
        anomalia = self._detectar_anomalia(valor, historico)

        divergencia = self._calcular_divergencia(fontes) if n >= 2 else None
        precisa_revisao = bool(divergencia and divergencia > DIVERGENCIA_MAXIMA_PCT)

        # Se divergência alta mas dados confiáveis → rebaixar status
        if precisa_revisao and status == "VERIFICADO":
            status = "DIVERGENTE"

        hash_raw = self._hash_fontes(fontes)

        resultado = {
            "score_confianca": confianca,
            "status_verificacao": status,
            "bloqueado": bloqueado,
            "anomalia_detectada": anomalia["detectada"],
            "z_score": anomalia.get("z_score"),
            "desvio_entre_fontes_pct": divergencia,
            "revisao_humana": precisa_revisao,
            "hash_dado_raw": hash_raw,
            "n_fontes_independentes": n,
        }

        if salvar and not bloqueado and campo and entidade_id:
            await self._salvar(valor, campo, entidade_id, fontes, resultado)

        return resultado

    async def verificar_triangulado(
        self,
        campo: str,
        entidade_id: str,
        fontes_valores: dict[str, float],
    ) -> dict:
        """
        Recebe {nome_fonte: valor} e calcula valor final por mediana.
        Mais robusto que média para detectar outliers.
        """
        if not fontes_valores:
            return await self.verificar(0, [], campo, entidade_id)

        valores = list(fontes_valores.values())
        valor_final = statistics.median(valores)

        fontes = [
            {"nome": nome, "valor": v, "coletado_em": None}
            for nome, v in fontes_valores.items()
        ]
        return await self.verificar(valor_final, fontes, campo, entidade_id)

    def _filtrar_independentes(self, fontes: list[dict]) -> list[dict]:
        vistos = set()
        resultado = []
        for f in fontes:
            origem = f.get("nome", "")
            if origem not in vistos:
                vistos.add(origem)
                resultado.append(f)
        return resultado

    async def _get_historico(self, campo: str) -> list[float]:
        if not campo:
            return []
        try:
            result = await self.db.execute(
                select(DadoVerificado.valor_final)
                .where(DadoVerificado.campo == campo)
                .order_by(DadoVerificado.created_at.desc())
                .limit(30)
            )
            return [float(r[0]) for r in result.fetchall() if r[0] is not None]
        except Exception:
            return []

    def _detectar_anomalia(self, valor: float, historico: list[float]) -> dict:
        if len(historico) < 5:
            return {"detectada": False, "z_score": None}
        try:
            media = statistics.mean(historico)
            desvio = statistics.stdev(historico)
            if desvio == 0:
                return {"detectada": False, "z_score": 0.0}
            z = (valor - media) / desvio
            return {"detectada": abs(z) > ZSCORE_ANOMALIA, "z_score": round(z, 3)}
        except Exception:
            return {"detectada": False, "z_score": None}

    def _calcular_divergencia(self, fontes: list[dict]) -> float | None:
        valores = [f.get("valor") for f in fontes if f.get("valor") is not None]
        if len(valores) < 2:
            return None
        try:
            media = statistics.mean(valores)
            if media == 0:
                return None
            desvio = max(valores) - min(valores)
            return round((desvio / abs(media)) * 100, 2)
        except Exception:
            return None

    def _hash_fontes(self, fontes: list[dict]) -> str:
        payload = json.dumps(fontes, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    async def _salvar(
        self,
        valor: float,
        campo: str,
        entidade_id: str,
        fontes: list[dict],
        resultado: dict,
    ):
        try:
            import uuid
            dado = DadoVerificado(
                entidade_id=uuid.UUID(entidade_id) if entidade_id else None,
                campo=campo,
                valor_final=valor,
                fontes=fontes,
                n_fontes_independentes=resultado["n_fontes_independentes"],
                desvio_entre_fontes_pct=resultado["desvio_entre_fontes_pct"],
                score_confianca=resultado["score_confianca"],
                status_verificacao=resultado["status_verificacao"],
                anomalia_detectada=resultado["anomalia_detectada"],
                z_score=resultado["z_score"],
                revisao_humana=resultado["revisao_humana"],
                hash_dado_raw=resultado["hash_dado_raw"],
                agente_coletor="verificacao_service",
            )
            self.db.add(dado)
            await self.db.flush()
        except Exception as e:
            logger.warning(f"Falha ao salvar dado verificado: {e}")


# ─── Funções de conveniência (sem DB) ────────────────────────────────────────

def verificar_simples(valor: float, fontes: list[dict]) -> dict:
    """Verificação rápida sem persistência — para uso em coletores."""
    n = min(len({f.get("nome", i) for i, f in enumerate(fontes)}), 3)
    confianca, status, bloqueado = ESCALA_CONFIANCA[n]

    valores = [f.get("valor") for f in fontes if f.get("valor") is not None]
    divergencia = None
    if len(valores) >= 2:
        media = statistics.mean(valores)
        if media != 0:
            divergencia = round(((max(valores) - min(valores)) / abs(media)) * 100, 2)

    return {
        "score_confianca": confianca,
        "status_verificacao": status,
        "bloqueado": bloqueado,
        "n_fontes": n,
        "desvio_entre_fontes_pct": divergencia,
        "revisao_humana": bool(divergencia and divergencia > DIVERGENCIA_MAXIMA_PCT),
    }
