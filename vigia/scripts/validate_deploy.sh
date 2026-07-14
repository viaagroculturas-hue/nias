#!/bin/bash
# validate_deploy.sh — verifica saúde do deploy em produção
# Uso: bash scripts/validate_deploy.sh https://api-vigia.railway.app

set -euo pipefail

API_URL="${1:-https://api-vigia.railway.app}"
FRONTEND_URL="${2:-https://vigia.railway.app}"
PASS=0
FAIL=0

check() {
  local desc="$1"
  local cmd="$2"
  local expect="${3:-200}"

  printf "  %-45s" "${desc}..."
  code=$(eval "${cmd}" 2>/dev/null || echo "000")

  if [ "$code" = "$expect" ]; then
    echo "✓ ${code}"
    PASS=$((PASS + 1))
  else
    echo "✗ ${code} (esperado ${expect})"
    FAIL=$((FAIL + 1))
  fi
}

check_json() {
  local desc="$1"
  local url="$2"
  local field="$3"
  local value="$4"

  printf "  %-45s" "${desc}..."
  result=$(curl -sf "${url}" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('${field}',''))" 2>/dev/null || echo "")

  if [ "$result" = "$value" ]; then
    echo "✓ ${field}=${value}"
    PASS=$((PASS + 1))
  else
    echo "✗ ${field}=${result} (esperado ${value})"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "=== VIGÍA — Validação de Deploy ==="
echo "  API: ${API_URL}"
echo "  Frontend: ${FRONTEND_URL}"
echo ""

echo "── Backend ──────────────────────────────────────────────────"
check "GET /api/ping" \
  "curl -sf -o /dev/null -w '%{http_code}' '${API_URL}/api/ping'"
check_json "ping retorna status ok" \
  "${API_URL}/api/ping" "status" "ok"
check "GET /api/health" \
  "curl -sf -o /dev/null -w '%{http_code}' '${API_URL}/api/health'"
check "GET /api/radar/resumo" \
  "curl -sf -o /dev/null -w '%{http_code}' '${API_URL}/api/radar/resumo'"
check "GET /api/safra/culturas" \
  "curl -sf -o /dev/null -w '%{http_code}' '${API_URL}/api/safra/culturas'"
check "GET /api/mapa/municipios?limit=1" \
  "curl -sf -o /dev/null -w '%{http_code}' '${API_URL}/api/mapa/municipios?limit=1'"
echo ""

echo "── Frontend ─────────────────────────────────────────────────"
check "GET /" \
  "curl -sf -o /dev/null -w '%{http_code}' '${FRONTEND_URL}/'"
check "GET /mapa" \
  "curl -sf -o /dev/null -w '%{http_code}' '${FRONTEND_URL}/mapa'"
check "GET /clima" \
  "curl -sf -o /dev/null -w '%{http_code}' '${FRONTEND_URL}/clima'"
check "GET /mercado" \
  "curl -sf -o /dev/null -w '%{http_code}' '${FRONTEND_URL}/mercado'"
echo ""

echo "── Segurança ────────────────────────────────────────────────"
# CORS header deve estar presente
printf "  %-45s" "CORS header presente..."
cors=$(curl -sf -I -H "Origin: ${FRONTEND_URL}" "${API_URL}/api/ping" 2>/dev/null | grep -i "access-control" | wc -l || echo 0)
if [ "$cors" -gt 0 ]; then
  echo "✓"; PASS=$((PASS + 1))
else
  echo "✗ (sem CORS header)"; FAIL=$((FAIL + 1))
fi

# Não deve expor .env
printf "  %-45s" ".env não exposto publicamente..."
env_code=$(curl -sf -o /dev/null -w '%{http_code}' "${API_URL}/.env" 2>/dev/null || echo "000")
if [ "$env_code" = "404" ] || [ "$env_code" = "000" ]; then
  echo "✓ (${env_code})"; PASS=$((PASS + 1))
else
  echo "✗ ATENÇÃO: .env possivelmente exposto (${env_code})"; FAIL=$((FAIL + 1))
fi
echo ""

echo "── Resultado ────────────────────────────────────────────────"
echo "  Passou: ${PASS}"
echo "  Falhou: ${FAIL}"
echo ""

if [ "$FAIL" -eq 0 ]; then
  echo "✓ Deploy validado com sucesso!"
  exit 0
else
  echo "✗ ${FAIL} verificação(ões) falharam — revisar antes de ir a ar"
  exit 1
fi
