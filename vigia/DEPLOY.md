# VIGÍA — Deploy em Produção (Railway)

## Pré-requisitos

- Conta Railway: railway.app
- CLI: `npm install -g @railway/cli` && `railway login`
- Repositório GitHub conectado ao Railway

---

## 1. Criar projeto Railway

```bash
cd vigia
railway init    # criar projeto novo
railway link    # ou vincular a projeto existente
```

---

## 2. Adicionar PostgreSQL e Redis (plugins Railway)

No painel Railway → **New Service** → **Database**:

1. **PostgreSQL** → Railway injeta `DATABASE_URL` automaticamente
2. **Redis** → Railway injeta `REDIS_URL` automaticamente

---

## 3. Criar os 4 serviços

Railway não cria múltiplos serviços via `railway.toml` em monorepo — configure cada um no painel.

Para ver os comandos exatos:
```bash
bash scripts/railway_services.sh
```

Resumo de cada serviço:

| Serviço | Root Directory | Start Command |
|---|---|---|
| `backend` | `vigia/backend` | `/app/entrypoint.sh` |
| `celery_worker` | `vigia/backend` | `celery -A celery_app worker --loglevel=warning --concurrency=2` |
| `celery_beat` | `vigia/backend` | `celery -A celery_app beat --loglevel=warning --schedule /tmp/celerybeat-schedule` |
| `frontend` | `vigia/frontend` | `node server.js` |

> O `entrypoint.sh` roda `alembic upgrade head` automaticamente antes de subir o uvicorn.

---

## 4. Configurar Secrets

```bash
bash scripts/setup_railway.sh --service backend
```

O script solicita cada variável interativamente e configura via `railway variables set`.

Repita para `celery_worker` e `celery_beat` com as mesmas variáveis (exceto `APP_URL`/`API_URL`).

Variáveis obrigatórias:

```
JWT_SECRET                    # gerado automaticamente pelo script
ANTHROPIC_API_KEY             # sk-ant-...
TWILIO_ACCOUNT_SID            # ACxxxx (se usar WhatsApp/SMS)
TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_FROM          # whatsapp:+14155238886
NOTIFICACAO_DESTINOS_WHATSAPP # +5511999999999,...
APP_ENV=production
APP_URL                       # https://vigia.railway.app
API_URL                       # https://api-vigia.railway.app
```

Variáveis opcionais:

```
SENTRY_DSN                    # https://xxx@oyyy.ingest.sentry.io/zzz
GEE_SERVICE_ACCOUNT           # se usar satélite real (não simulado)
TWILIO_SMS_FROM
NOTIFICACAO_DESTINOS_SMS
```

Variável de build do frontend:

```
NEXT_PUBLIC_API_URL           # https://api-vigia.railway.app
```

---

## 5. Deploy

```bash
make railway-deploy-all
# ou manualmente:
railway up --service backend
railway up --service celery_worker
railway up --service celery_beat
railway up --service frontend
```

As migrações Alembic rodam automaticamente no boot do `backend` via `entrypoint.sh`.
O seed autônomo (4.500+ municípios, 85 culturas) roda no primeiro boot automaticamente.

---

## 6. Validar deploy

```bash
bash scripts/validate_deploy.sh https://api-vigia.railway.app https://vigia.railway.app
```

Ou:
```bash
make validate
```

Verifica: ping, health, CORS, rotas principais, frontend, segurança.

---

## 7. SSL

Railway provisiona SSL automaticamente para domínios `.railway.app`.

Para domínio customizado:
1. Railway → seu serviço → **Settings** → **Custom Domains** → adicionar domínio
2. Configurar DNS (CNAME para o domínio Railway)
3. Atualizar variáveis `APP_URL`, `API_URL`, `NEXT_PUBLIC_API_URL`
4. SSL renovado automaticamente via Let's Encrypt

---

## 8. Sentry (monitoramento de erros)

1. Criar projeto em sentry.io → **Python / FastAPI**
2. Copiar o DSN
3. `railway variables set "SENTRY_DSN=https://xxx@oyyy.ingest.sentry.io/zzz" --service backend`
4. Verificar: Sentry só ativa quando `APP_ENV=production` — seguro em dev local

---

## 9. UptimeRobot (monitoramento 24/7)

1. Cadastre em uptimerobot.com (plano gratuito: 50 monitores, 5min intervalo)
2. **New Monitor** → HTTP(s) para cada URL:

| Monitor | URL | Intervalo |
|---|---|---|
| VIGÍA API | `https://api-vigia.railway.app/api/health` | 5 min |
| VIGÍA Frontend | `https://vigia.railway.app` | 5 min |
| Relatório (opcional) | `https://api-vigia.railway.app/api/relatorio/hoje` | 30 min |

3. **Alert Contacts**: email + webhook Slack/Discord (opcional)
4. **Status Page**: crie uma página pública de status para transparência

---

## 10. Logs em tempo real

```bash
make railway-logs-backend
# ou:
railway logs --service backend --tail
railway logs --service celery_worker --tail
railway logs --service celery_beat --tail
```

---

## Operações comuns

```bash
# Rodar migrações manualmente
make railway-migrate

# Shell dentro do container backend
railway run --service backend bash

# Forçar ciclo de agentes manualmente
curl -X POST https://api-vigia.railway.app/api/inteligencia/agentes/executar \
  -H "Authorization: Bearer $TOKEN"

# Rollback
railway rollback --service backend
```

---

## Checklist final pré-produção

- [ ] `GET /api/health` retorna `{"status": "healthy"}`
- [ ] `GET /api/ping` retorna `{"status": "ok", "sistema": "VIGÍA"}`
- [ ] Frontend carrega sem erros de CORS no console
- [ ] WebSocket `/api/radar/ws` conecta (abrir DevTools → Network → WS)
- [ ] Celery Beat aparece nos logs (schedule carregado)
- [ ] Celery Worker aparece nos logs (pronto para tasks)
- [ ] Seed autônomo concluído (ver logs do backend, etapa 10/10)
- [ ] UptimeRobot enviou primeiro check verde
- [ ] Sentry recebeu evento de teste (se configurado)
- [ ] Relatório 05h30 disparado no dia seguinte (ver logs `celery_beat`)
- [ ] Notificação WhatsApp de teste enviada:
  `curl -X POST https://api-vigia.railway.app/api/inteligencia/notificacao/teste`
- [ ] SSL válido em ambos os domínios
- [ ] `.env` não acessível publicamente: `curl https://api-vigia.railway.app/.env` → 404
