# VIGÍA — Makefile
# Uso: make <target>

.PHONY: dev prod build migrate seed logs validate shell-backend

# ── Dev local ─────────────────────────────────────────────────────

dev:
	docker compose -f docker-compose.yml up

dev-build:
	docker compose -f docker-compose.yml up --build

# ── Produção (docker-compose.prod.yml) ────────────────────────────

prod:
	docker compose -f docker-compose.prod.yml up -d

prod-build:
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f --tail=100

# ── Banco ─────────────────────────────────────────────────────────

migrate:
	docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

migrate-dev:
	cd backend && alembic upgrade head

migrate-new:
	cd backend && alembic revision --autogenerate -m "$(name)"

# ── Seed ──────────────────────────────────────────────────────────

seed:
	docker compose -f docker-compose.prod.yml exec backend \
	  python -c "import asyncio; from tasks.seed_autonomo import executar_seed; asyncio.run(executar_seed())"

# ── Agentes ───────────────────────────────────────────────────────

run-agents:
	docker compose -f docker-compose.prod.yml exec backend \
	  python -c "import asyncio; from database import AsyncSessionLocal; from agents import executar_todos_agentes; asyncio.run(executar_todos_agentes.__wrapped__(AsyncSessionLocal()))"

# ── Railway ───────────────────────────────────────────────────────

railway-setup:
	bash scripts/setup_railway.sh

railway-services:
	bash scripts/railway_services.sh

railway-deploy-all:
	railway up --service backend
	railway up --service celery_worker
	railway up --service celery_beat
	railway up --service frontend

railway-logs-backend:
	railway logs --service backend --tail

railway-migrate:
	railway run --service backend alembic upgrade head

# ── Validação ─────────────────────────────────────────────────────

validate:
	@read -p "API URL: " api && read -p "Frontend URL: " fe && \
	bash scripts/validate_deploy.sh "$$api" "$$fe"

# ── Shell ─────────────────────────────────────────────────────────

shell-backend:
	docker compose -f docker-compose.prod.yml exec backend bash

shell-db:
	docker compose -f docker-compose.prod.yml exec postgres psql -U vigia vigia_db
