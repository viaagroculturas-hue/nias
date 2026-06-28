#!/bin/bash
BASE=${1:-http://localhost:8000}
KEY=${NIAS_API_KEY:-""}

check() {
  code=$(curl -s -o /dev/null -w "%{http_code}" -H "X-NIAS-Key: $KEY" "$BASE$1")
  echo "$1 → HTTP $code"
  [ "$code" = "200" ] && echo "  ✓ OK" || echo "  ✗ FALHOU"
}

echo "=== NIAS v2 Smoke Tests ==="
echo "Base: $BASE"
echo ""

check /api/health
check /api/polos
check "/api/polos?pais=BR"
check "/api/polos?cultura=soja"
check /api/ceasa/all
check /api/ceasa/go
check /api/ceasa/mg
check /api/ceasa/rn
check /api/cepea
check /api/clima/bioclima
check /api/alerts/active
check /api/situation/real
check /api/satellite/analysis
check /api/polo/br_sorriso
check /api/polo/ar_rosario
check /api/polo/polo_inexistente   # deve retornar 404

echo ""
echo "=== Fim dos testes ==="
