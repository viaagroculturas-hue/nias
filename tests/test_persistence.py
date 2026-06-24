"""
Testes v3.3: Persistência, Scheduler Logs, Sources, Credentials
"""
import urllib.request, json, sys

BASE = 'http://localhost:8080'

def test(name, url, check_fn):
    try:
        req = urllib.request.Request(f'{BASE}{url}')
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
            ok = check_fn(data)
            print(f'  [{"OK" if ok else "FAIL"}] {name}')
            if not ok:
                print(f'       Response: {json.dumps(data, ensure_ascii=False)[:300]}')
            return ok
    except Exception as e:
        print(f'  [FAIL] {name} — {e}')
        return False

print('=' * 60)
print('TESTE v3.3: Persistência, Scheduler, Sources, CLIMAPI')
print('=' * 60)

results = []

# Pipeline endpoints
results.append(test('/api/pipeline/status', '/api/pipeline/status',
    lambda d: 'storage' in d and 'freshness' in d and 'running' in d))

results.append(test('/api/pipeline/runs', '/api/pipeline/runs',
    lambda d: 'runs' in d and isinstance(d['runs'], list)))

results.append(test('/api/pipeline/logs', '/api/pipeline/logs',
    lambda d: 'lines' in d and isinstance(d['lines'], list)))

results.append(test('/api/pipeline/freshness', '/api/pipeline/freshness',
    lambda d: 'prices' in d and 'climate' in d and 'news' in d and 'macro' in d))

# Sources status — CEPEA + CLIMAPI diagnosticados
results.append(test('/api/sources/status — CEPEA fallback', '/api/sources/status',
    lambda d: d.get('sources', {}).get('cepea', {}).get('status') == 'fallback'))

results.append(test('/api/sources/status — CLIMAPI com diagnostico', '/api/sources/status',
    lambda d: 'status' in d.get('sources', {}).get('climapi', {})))

results.append(test('/api/sources/status — storage info', '/api/sources/status',
    lambda d: 'storage' in d and 'persistent' in d.get('storage', {})))

# Climate endpoints preservados
results.append(test('/api/climate/status', '/api/climate/status',
    lambda d: d.get('module') == 'NiasClimate'))

# Não deve expor valores de secrets (chaves, tokens, passwords)
results.append(test('No secret values in sources', '/api/sources/status',
    lambda d: all(pat not in json.dumps(d) for pat in ['PLAK1', 'AIzaSy', 'sh-', 'Bearer ey'])))

# Pipeline status tem storage type
results.append(test('Storage type in pipeline/status', '/api/pipeline/status',
    lambda d: d.get('storage', {}).get('type') in ('sqlite', 'postgres')))

passed = sum(results)
failed = len(results) - passed
print(f'\nResultado: {passed}/{len(results)} passed, {failed} failed')
if failed:
    sys.exit(1)
