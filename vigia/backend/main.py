from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from database import create_tables, AsyncSessionLocal
from config import get_settings
from routers import radar, mapa, safra, clima, mercado, pragas, operacoes
from routers import inteligencia, satelite, demanda, relatorio, auth, seed
from routers import health

settings = get_settings()
logger = logging.getLogger(__name__)

# ── Sentry — só em produção, nunca obrigatório ───────────────────
if settings.app_env == "production":
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        _dsn = settings.sentry_dsn
        if _dsn:
            sentry_sdk.init(
                dsn=_dsn,
                integrations=[FastApiIntegration(), SqlalchemyIntegration()],
                traces_sample_rate=0.1,
                environment=settings.app_env,
                release="vigia@1.0.0",
            )
            logger.info("Sentry inicializado")
    except ImportError:
        pass


async def _auto_seed():
    """Dispara o seed autônomo se ainda não foi executado."""
    try:
        from sqlalchemy import select
        from models.inteligencia import SeedStatus

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SeedStatus).where(SeedStatus.status == "concluido").limit(1)
            )
            ja_concluido = result.scalar_one_or_none()

        if ja_concluido:
            logger.info("VIGÍA — seed já executado anteriormente, pulando")
            return

        logger.info("VIGÍA — primeiro boot detectado, iniciando seed autônomo")
        from tasks.seed_autonomo import executar_seed
        await executar_seed()

    except Exception as e:
        logger.error(f"Auto-seed erro: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    logger.info("VIGÍA iniciado — tabelas criadas")
    # Seed roda em background para não bloquear o startup
    asyncio.create_task(_auto_seed())
    yield
    logger.info("VIGÍA encerrando")


app = FastAPI(
    title="VIGÍA — Inteligência Agroestratégica",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/api/auth",         tags=["auth"])
app.include_router(radar.router,        prefix="/api/radar",        tags=["radar"])
app.include_router(mapa.router,         prefix="/api/mapa",         tags=["mapa"])
app.include_router(safra.router,        prefix="/api/safra",        tags=["safra"])
app.include_router(clima.router,        prefix="/api/clima",        tags=["clima"])
app.include_router(mercado.router,      prefix="/api/mercado",      tags=["mercado"])
app.include_router(pragas.router,       prefix="/api/pragas",       tags=["pragas"])
app.include_router(operacoes.router,    prefix="/api/operacoes",    tags=["operacoes"])
app.include_router(inteligencia.router, prefix="/api/inteligencia", tags=["inteligencia"])
app.include_router(satelite.router,     prefix="/api/satelite",     tags=["satelite"])
app.include_router(demanda.router,      prefix="/api/demanda",      tags=["demanda"])
app.include_router(relatorio.router,    prefix="/api/relatorio",    tags=["relatorio"])
app.include_router(seed.router,         prefix="/api/seed",         tags=["seed"])
app.include_router(health.router,       prefix="/api/health",       tags=["health"])


@app.get("/api/ping")
async def ping():
    return {"status": "ok", "sistema": "VIGÍA", "versao": "1.0.0"}
