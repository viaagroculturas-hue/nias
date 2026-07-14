#!/bin/bash
# setup_railway.sh — configura variáveis de ambiente no Railway
# Pré-requisito: railway login && railway link
# Uso: bash scripts/setup_railway.sh --service backend

set -euo pipefail

SERVICE="${1:---service backend}"

echo "=== VIGÍA — Railway Secrets Setup ==="
echo ""

prompt() {
  local var="$1"
  local desc="$2"
  local default="${3:-}"

  if [ -n "$default" ]; then
    read -rp "  ${var} [${desc}] (default: ${default}): " val
    val="${val:-$default}"
  else
    read -rsp "  ${var} [${desc}]: " val
    echo ""
  fi

  if [ -n "$val" ]; then
    railway variables set "${var}=${val}" ${SERVICE}
    echo "  ✓ ${var} configurado"
  else
    echo "  — ${var} ignorado (vazio)"
  fi
}

echo "── Banco de dados ────────────────────────────────────────────"
echo "  (Railway injeta DATABASE_URL automaticamente via plugin PostgreSQL)"
echo ""

echo "── Auth ──────────────────────────────────────────────────────"
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
echo "  JWT_SECRET gerado automaticamente: ${JWT_SECRET:0:12}..."
railway variables set "JWT_SECRET=${JWT_SECRET}" ${SERVICE}
echo "  ✓ JWT_SECRET configurado"
echo ""

echo "── IA — Anthropic ────────────────────────────────────────────"
prompt "ANTHROPIC_API_KEY" "sk-ant-..."
echo ""

echo "── Notificações — Twilio ─────────────────────────────────────"
prompt "TWILIO_ACCOUNT_SID" "ACxxxx"
prompt "TWILIO_AUTH_TOKEN" "token"
prompt "TWILIO_WHATSAPP_FROM" "whatsapp:+14155238886" "whatsapp:+14155238886"
prompt "TWILIO_SMS_FROM" "+1500xxxxx"
prompt "NOTIFICACAO_DESTINOS_WHATSAPP" "+5511999999999 (vírgula para múltiplos)"
prompt "NOTIFICACAO_DESTINOS_SMS" "+5511999999999"
echo ""

echo "── Sentry (opcional) ─────────────────────────────────────────"
prompt "SENTRY_DSN" "https://xxx@oyyy.ingest.sentry.io/zzz"
echo ""

echo "── App ───────────────────────────────────────────────────────"
prompt "APP_URL" "https://vigia.railway.app"
prompt "API_URL" "https://api-vigia.railway.app"
railway variables set "APP_ENV=production" ${SERVICE}
railway variables set "RELATORIO_HORA=05:30" ${SERVICE}
railway variables set "RELATORIO_TIMEZONE=America/Sao_Paulo" ${SERVICE}
echo ""

echo "=== Configuração concluída ==="
echo "Próximo passo: railway up"
