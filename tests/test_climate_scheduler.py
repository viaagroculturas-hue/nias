"""
Testes do Scheduler e Pipeline Status
"""
import urllib.request, json, sys

BASE = 'http://localhost:8080'

def test(name, url, check_fn):
    try:
        req = urllib.request.Request(f'{BASE}{url}')
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode())
            ok = check_fn(data)
            print(f'  [{"OK" if ok else "FAIL"}] {name}')
            if not ok:
                print(f'       Response: {json.dumps(data, ensure_ascii=False)[:200]}')
            return ok
    except Exception as e:
        print(f'  [FAIL] {name} — {e}')
        return False

print('=' * 60)
print('TESTE: Scheduler + Sources + Climate')
print('=' * 60)

results = []

# Pipeline
results.append(test('/api/pipeline/status', '/api/pipeline/status',
    lambda d: 'running' in d or 'freshness' in d))

# Sources
results.append(test('/api/sources/status', '/api/sources/status',
    lambda d: 'sources' in d and 'conab' in d['sources'] and 'cepea' in d['sources']))

# Climate
results.append(test('/api/climate/status', '/api/climate/status',
    lambda d: d.get('status') == 'ok' and d.get('module') == 'NiasClimate'))

results.append(test('/api/climate/alerts', '/api/climate/alerts',
    lambda d: 'alerts' in d and 'total' in d))

results.append(test('/api/climate/price-impact', '/api/climate/price-impact',
    lambda d: 'items' in d and d.get('status') in ('ok', 'partial', 'insufficient_data')))

results.append(test('/api/climate/report', '/api/climate/report',
    lambda d: 'resumo' in d and 'regioes_monitoradas' in d))

results.append(test('/api/climate/regions', '/api/climate/regions',
    lambda d: 'regions' in d and d.get('total', 0) == 12))

results.append(test('/api/climate/events', '/api/climate/events',
    lambda d: 'events' in d and 'total' in d))

passed = sum(results)
failed = len(results) - passed
print(f'\nResultado: {passed}/{len(results)} passed, {failed} failed')
if failed:
    sys.exit(1)
