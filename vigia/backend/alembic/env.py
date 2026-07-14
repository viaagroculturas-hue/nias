import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Importar todos os modelos para que o metadata capture as tabelas
from database import Base   # noqa: F401
import models.geo            # noqa: F401
import models.cultura        # noqa: F401
import models.safra          # noqa: F401
import models.clima          # noqa: F401
import models.pragas         # noqa: F401
import models.mercado        # noqa: F401
import models.demanda        # noqa: F401
import models.satelite       # noqa: F401
import models.viveiros       # noqa: F401
import models.inteligencia   # noqa: F401
import models.operacoes      # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL vem da variável de ambiente — sobrescreve o alembic.ini
# Render injeta 'postgres://' — normalizar para psycopg2 síncrono
database_url = os.environ.get("DATABASE_URL", "")
sync_url = (
    database_url
    .replace("postgres://", "postgresql://", 1)
    .replace("postgresql+asyncpg://", "postgresql://")
)
if sync_url:
    config.set_main_option("sqlalchemy.url", sync_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    async_url = (
        database_url
        .replace("postgres://", "postgresql://", 1)
        .replace("postgresql://", "postgresql+asyncpg://", 1)
    ) if database_url else ""
    cfg = config.get_section(config.config_ini_section, {})
    if async_url:
        cfg["sqlalchemy.url"] = async_url

    connectable = async_engine_from_config(
        cfg,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
