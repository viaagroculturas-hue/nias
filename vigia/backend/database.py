from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from config import get_settings

settings = get_settings()


def _normalizar_url(url: str) -> str:
    # Render injeta 'postgres://' mas SQLAlchemy 2+ exige 'postgresql+asyncpg://'
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    # asyncpg não aceita sslmode= na query string
    if "sslmode=" in url:
        from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
        parsed = urlparse(url)
        qs = {k: v for k, v in parse_qs(parsed.query).items() if k != "sslmode"}
        url = urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))
    return url


_db_url = _normalizar_url(settings.database_url)
_is_prod = settings.app_env == "production"

engine = create_async_engine(
    _db_url,
    echo=not _is_prod,
    pool_size=3 if _is_prod else 5,
    max_overflow=7 if _is_prod else 10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
