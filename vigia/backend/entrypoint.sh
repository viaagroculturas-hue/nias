#!/bin/sh
set -e

echo "VIGÍA — executando migrações Alembic..."
alembic upgrade head

echo "VIGÍA — iniciando servidor..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WORKERS:-2}"
