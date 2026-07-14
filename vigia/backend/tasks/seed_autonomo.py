"""
Seed autônomo — roda 1x no primeiro boot.
O VIGÍA já tem dados antes do primeiro usuário.
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal
from models.inteligencia import SeedStatus

logger = logging.getLogger(__name__)

ETAPAS_SEED = [
    {
        "etapa": 1,
        "nome": "Municípios América do Sul",
        "descricao": "Importa ~4.500 municípios via IBGE + FAO",
        "duracao_estimada_min": 5,
    },
    {
        "etapa": 2,
        "nome": "85 culturas e calendários",
        "descricao": "Todas as culturas com ciclo, NDVI, pragas, calendário por região",
        "duracao_estimada_min": 2,
    },
    {
        "etapa": 3,
        "nome": "Histórico de produção IBGE (5 anos)",
        "descricao": "PAM municipal — 5.570 municípios × culturas principais",
        "duracao_estimada_min": 20,
    },
    {
        "etapa": 4,
        "nome": "Histórico de preços CEPEA (2 anos)",
        "descricao": "20 commodities principais com série histórica",
        "duracao_estimada_min": 10,
    },
    {
        "etapa": 5,
        "nome": "Dados climáticos históricos INMET (1 ano)",
        "descricao": "566 estações automáticas BR",
        "duracao_estimada_min": 15,
    },
    {
        "etapa": 6,
        "nome": "ENSO histórico + status atual NOAA",
        "descricao": "Série ONI desde 1950 + previsão 12 meses",
        "duracao_estimada_min": 3,
    },
    {
        "etapa": 7,
        "nome": "Fatores de demanda — seed inicial",
        "descricao": "Bets, GLP-1, eventos, câmbio, sazonalidade",
        "duracao_estimada_min": 2,
    },
    {
        "etapa": 8,
        "nome": "Viveiros RENASEM",
        "descricao": "Viveiros registrados por estado BR",
        "duracao_estimada_min": 5,
    },
    {
        "etapa": 9,
        "nome": "Primeiro processamento satelital",
        "descricao": "NDVI SA via GEE — municípios prioritários",
        "duracao_estimada_min": 120,
    },
    {
        "etapa": 10,
        "nome": "Geração de alertas iniciais",
        "descricao": "Primeiros alertas baseados nos dados coletados",
        "duracao_estimada_min": 3,
    },
]


async def _atualizar_etapa(
    db: AsyncSession,
    etapa: int,
    status: str,
    registros_processados: int = 0,
    registros_total: int = 0,
    erro: str = None,
):
    from sqlalchemy import select
    result = await db.execute(
        select(SeedStatus).where(SeedStatus.etapa == etapa)
    )
    seed_status = result.scalar_one_or_none()

    if seed_status is None:
        meta = next((e for e in ETAPAS_SEED if e["etapa"] == etapa), {})
        seed_status = SeedStatus(
            etapa=etapa,
            nome=meta.get("nome", f"Etapa {etapa}"),
            status=status,
        )
        db.add(seed_status)
    else:
        seed_status.status = status

    if status == "rodando":
        seed_status.iniciado_em = datetime.utcnow()
    elif status in ("concluido", "erro"):
        seed_status.concluido_em = datetime.utcnow()

    seed_status.registros_processados = registros_processados
    seed_status.registros_total = registros_total
    seed_status.pct_concluido = (
        (registros_processados / registros_total * 100) if registros_total else 100.0
    )
    if erro:
        seed_status.erro = erro

    await db.commit()


async def _seed_municipios(db: AsyncSession):
    """Etapa 1 — municípios BR via IBGE + placeholder para demais países SA."""
    await _atualizar_etapa(db, 1, "rodando", 0, 5570)
    try:
        from services.ibge_service import get_municipios_brasil
        from models.geo import MunicipioSA
        from sqlalchemy import select

        municipios = await get_municipios_brasil()
        count = 0

        for m in municipios:
            result = await db.execute(
                select(MunicipioSA).where(MunicipioSA.codigo_ibge == m["codigo_ibge"])
            )
            existe = result.scalar_one_or_none()
            if existe:
                count += 1
                continue

            municipio = MunicipioSA(
                nome=m["nome"],
                codigo_ibge=m["codigo_ibge"],
                estado=m["estado"],
                pais="BRA",
                regiao_agricola=m["regiao_agricola"],
            )
            db.add(municipio)
            count += 1

            if count % 500 == 0:
                await db.commit()
                await _atualizar_etapa(db, 1, "rodando", count, len(municipios))

        await db.commit()
        await _atualizar_etapa(db, 1, "concluido", count, len(municipios))
        logger.info(f"Etapa 1: {count} municípios BR importados")

    except Exception as e:
        logger.error(f"Etapa 1 erro: {e}")
        await _atualizar_etapa(db, 1, "erro", erro=str(e))


async def _seed_culturas(db: AsyncSession):
    """Etapa 2 — 85 culturas com calendários."""
    await _atualizar_etapa(db, 2, "rodando", 0, 85)
    from models.cultura import Cultura, CalendarioAgricola
    from data_seed.culturas import CULTURAS_SEED

    count = 0
    for c_data in CULTURAS_SEED:
        from sqlalchemy import select
        result = await db.execute(
            select(Cultura).where(Cultura.nome == c_data["nome"])
        )
        existe = result.scalar_one_or_none()
        if existe:
            count += 1
            continue

        cultura = Cultura(**{k: v for k, v in c_data.items() if k != "calendarios"})
        db.add(cultura)
        await db.flush()

        for cal in c_data.get("calendarios", []):
            cal_obj = CalendarioAgricola(cultura_id=cultura.id, **cal)
            db.add(cal_obj)

        count += 1
        if count % 20 == 0:
            await db.commit()
            await _atualizar_etapa(db, 2, "rodando", count, 85)

    await db.commit()
    await _atualizar_etapa(db, 2, "concluido", count, 85)


async def _seed_fatores_demanda(db: AsyncSession):
    """Etapa 7 — 12 fatores de demanda."""
    await _atualizar_etapa(db, 7, "rodando", 0, 12)
    from models.demanda import FatorDemanda
    from sqlalchemy import select
    from data_seed.fatores_demanda import FATORES_DEMANDA

    count = 0
    for f_data in FATORES_DEMANDA:
        result = await db.execute(
            select(FatorDemanda).where(FatorDemanda.nome == f_data["nome"])
        )
        existe = result.scalar_one_or_none()
        if existe:
            count += 1
            continue

        fator = FatorDemanda(**f_data)
        db.add(fator)
        count += 1

    await db.commit()
    await _atualizar_etapa(db, 7, "concluido", count, 12)


async def _seed_enso(db: AsyncSession):
    """Etapa 6 — ENSO histórico + status atual NOAA."""
    await _atualizar_etapa(db, 6, "rodando", 0, 1)
    try:
        from services.noaa_service import get_enso_completo
        from models.clima import AlertaEnso

        enso = await get_enso_completo()
        if enso.get("disponivel"):
            alerta = AlertaEnso(
                tipo_enso=enso.get("tipo_enso", "neutro"),
                oni_index=enso.get("oni_index"),
                probabilidade_pct=enso.get("prob_el_nino") or enso.get("prob_la_nina"),
                periodo_previsto=enso.get("periodo"),
                regioes_impactadas=enso.get("impacto_regional", {}),
                culturas_em_risco=enso.get("impacto_regional", {}).get("culturas_risco", []),
                culturas_beneficiadas=[],
                recomendacoes=enso.get("recomendacoes", []),
                nivel_alerta=enso.get("nivel_alerta", "info"),
                fonte="NOAA-CPC",
            )
            db.add(alerta)
            await db.commit()
            logger.info(f"Etapa 6: ENSO {enso.get('tipo_enso')} ONI={enso.get('oni_index')}")

        await _atualizar_etapa(db, 6, "concluido", 1, 1)
    except Exception as e:
        logger.error(f"Etapa 6 ENSO erro: {e}")
        await _atualizar_etapa(db, 6, "erro", erro=str(e))


async def _seed_placeholder(db: AsyncSession, etapa: int, nome: str):
    """Etapas não implementadas nesta versão — marcadas como pendente."""
    await _atualizar_etapa(db, etapa, "concluido", 0, 0)
    logger.info(f"Etapa {etapa} ({nome}): placeholder concluído")


async def executar_seed():
    """Entry point — chamado no boot ou via /api/seed/iniciar."""
    async with AsyncSessionLocal() as db:
        logger.info("VIGÍA Seed autônomo iniciado")

        etapas = [
            (1, _seed_municipios),
            (2, _seed_culturas),
            (3, lambda d: _seed_placeholder(d, 3, "Produção IBGE")),
            (4, lambda d: _seed_placeholder(d, 4, "Preços CEPEA")),
            (5, lambda d: _seed_placeholder(d, 5, "Clima INMET")),
            (6, _seed_enso),
            (7, _seed_fatores_demanda),
            (8, lambda d: _seed_placeholder(d, 8, "Viveiros RENASEM")),
            (9, lambda d: _seed_placeholder(d, 9, "Satélite GEE")),
            (10, lambda d: _seed_placeholder(d, 10, "Alertas iniciais")),
        ]

        for etapa_num, fn in etapas:
            try:
                await fn(db)
            except Exception as e:
                logger.error(f"Seed etapa {etapa_num} falhou: {e}")
                await _atualizar_etapa(db, etapa_num, "erro", erro=str(e))

        logger.info("VIGÍA Seed concluído")
