"""
Testes para NIAS API Core v1 — /api/nias/*
"""
import json
import urllib.request
import sys
import time

BASE = 'http://localhost:8080'

def test(name, path, validator):
    try:
        url = BASE + path
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            code = resp.getcode()
            body = json.loads(resp.read().decode())
        # Validar envelope padrão
        has_envelope = body.get('api') == 'NIAS API Core' and body.get('version') == 'v1'
        if not has_envelope:
            return (name, False, f'Envelope NIAS ausente: {list(body.keys())[:5]}')
        if not validator(body):
            return (name, False, f'Validator falhou: {json.dumps(body, ensure_ascii=False)[:200]}')
        return (name, True, f'HTTP {code} OK')
    except Exception as e:
        return (name, False, str(e)[:200])

results = []

# 1. Status
results.append(test('/api/nias/status', '/api/nias/status',
    lambda d: d['status'] == 'ok' and 'data' in d and d['data'].get('service') == 'NIAS'))

# 2. Health
results.append(test('/api/nias/health', '/api/nias/health',
    lambda d: d['status'] == 'ok' and 'modules' in d.get('data', {})))

# 3. Docs
results.append(test('/api/nias/docs', '/api/nias/docs',
    lambda d: d['status'] == 'ok' and len(d['data'].get('endpoints', [])) >= 10))

# 4. Prices latest
results.append(test('/api/nias/prices/latest', '/api/nias/prices/latest',
    lambda d: d['status'] in ('ok', 'partial') and 'items' in d.get('data', {})))

# 5. Prices history
results.append(test('/api/nias/prices/history', '/api/nias/prices/history?product=tomate&limit=5',
    lambda d: d['status'] in ('ok', 'partial') and 'items' in d.get('data', {})))

# 6. Weather latest
results.append(test('/api/nias/weather/latest', '/api/nias/weather/latest',
    lambda d: d['status'] in ('ok', 'partial') and 'items' in d.get('data', {})))

# 7. Weather risk
results.append(test('/api/nias/weather/risk', '/api/nias/weather/risk',
    lambda d: d['status'] == 'ok' and 'events' in d.get('data', {})))

# 8. Intelligence weather-price
results.append(test('/api/nias/intelligence/weather-price', '/api/nias/intelligence/weather-price',
    lambda d: d['status'] in ('ok', 'partial') and 'items' in d.get('data', {})))

# 9. Intelligence opportunities
results.append(test('/api/nias/intelligence/opportunities', '/api/nias/intelligence/opportunities',
    lambda d: d['status'] == 'ok' and 'opportunities' in d.get('data', {})))

# 10. Intelligence predictions
results.append(test('/api/nias/intelligence/predictions', '/api/nias/intelligence/predictions',
    lambda d: d['status'] == 'ok' and 'predictions' in d.get('data', {})))

# 11. Intelligence alerts
results.append(test('/api/nias/intelligence/alerts', '/api/nias/intelligence/alerts',
    lambda d: d['status'] == 'ok' and 'alerts' in d.get('data', {})))

# 12. Report daily
results.append(test('/api/nias/report/daily', '/api/nias/report/daily',
    lambda d: d['status'] == 'ok' and 'data' in d))

# 13. Sources status
results.append(test('/api/nias/sources/status', '/api/nias/sources/status',
    lambda d: d['status'] == 'ok' and 'sources' in d.get('data', {})))

# 14. Pipeline status
results.append(test('/api/nias/pipeline/status', '/api/nias/pipeline/status',
    lambda d: d['status'] == 'ok' and 'data' in d))

# 15. Pipeline freshness
results.append(test('/api/nias/pipeline/freshness', '/api/nias/pipeline/freshness',
    lambda d: d['status'] == 'ok' and 'data' in d))

# 16. Pipeline runs
results.append(test('/api/nias/pipeline/runs', '/api/nias/pipeline/runs',
    lambda d: d['status'] == 'ok' and 'runs' in d.get('data', {})))

# 17. 404 retorna erro formatado
results.append(test('/api/nias/inexistente', '/api/nias/inexistente',
    lambda d: d['status'] == 'error' and 'message' in d))

# 18. Endpoints antigos ainda funcionam
def test_legacy(name, path, key):
    try:
        url = BASE + path
        with urllib.request.urlopen(url, timeout=30) as resp:
            body = json.loads(resp.read().decode())
        # Antigos NÃO têm envelope NIAS — confirmar que ainda retornam dados
        if key and key not in body and key not in str(body):
            return (name, False, f'Chave {key} ausente no legacy')
        return (name, True, f'Legacy OK')
    except Exception as e:
        return (name, False, str(e)[:200])

results.append(test_legacy('Legacy /api/health', '/api/health', 'status'))
results.append(test_legacy('Legacy /api/pipeline/status', '/api/pipeline/status', 'running'))
results.append(test_legacy('Legacy /api/sources/status', '/api/sources/status', 'sources'))
results.append(test_legacy('Legacy /api/climate/price-impact', '/api/climate/price-impact', 'items'))
results.append(test_legacy('Legacy /api/intelligence/opportunities', '/api/intelligence/opportunities', 'opportunities'))

# Resultado
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f'\n=== NIAS API Core Tests: {passed}/{total} ===')
for name, ok, detail in results:
    status = 'PASS' if ok else 'FAIL'
    print(f'  [{status}] {name}: {detail}')

if passed < total:
    print(f'\nFAILED: {total - passed} teste(s) falharam')
    sys.exit(1)
else:
    print(f'\nTodos os {total} testes passaram!')
    sys.exit(0)
