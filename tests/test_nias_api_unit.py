"""Quick test: verifica se o server.py inicia e importa NIAS API Core sem erros."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Test 1: Import do módulo
try:
    from flv.nias_api import API_NAME, API_VERSION
    from flv.nias_api import responses as R
    from flv.nias_api.router import _dispatch
    assert API_NAME == 'NIAS API Core'
    assert API_VERSION == 'v1'
    print('[PASS] Import NIAS API Core OK')
except Exception as e:
    print(f'[FAIL] Import: {e}')
    sys.exit(1)

# Test 2: Envelope ok()
r = R.ok({'test': True}, sources=['X'], confidence='alta')
assert r['status'] == 'ok'
assert r['api'] == 'NIAS API Core'
assert r['version'] == 'v1'
assert r['data']['test'] is True
assert r['meta']['sources'] == ['X']
print('[PASS] R.ok() envelope OK')

# Test 3: Envelope error()
r = R.error('boom', 'details')
assert r['status'] == 'error'
assert r['message'] == 'boom'
print('[PASS] R.error() envelope OK')

# Test 4: Envelope partial()
r = R.partial({'items': []}, 'sem dados', missing=['foo'])
assert r['status'] == 'partial'
assert r['mode'] == 'insufficient_data'
print('[PASS] R.partial() envelope OK')

# Test 5: Dispatch status
r = _dispatch('status', {})
assert r['status'] == 'ok'
assert r['data']['service'] == 'NIAS'
print('[PASS] _dispatch("status") OK')

# Test 6: Dispatch docs
r = _dispatch('docs', {})
assert r['status'] == 'ok'
assert len(r['data']['endpoints']) >= 10
print(f'[PASS] _dispatch("docs") OK — {len(r["data"]["endpoints"])} endpoints')

# Test 7: Dispatch health
r = _dispatch('health', {})
assert r['status'] == 'ok'
assert 'modules' in r['data']
print('[PASS] _dispatch("health") OK')

# Test 8: Dispatch 404
r = _dispatch('inexistente/xyz', {})
assert r['status'] == 'error'
print('[PASS] _dispatch("inexistente") -> error OK')

# Test 9: Dispatch prices/latest
r = _dispatch('prices/latest', {})
assert r['status'] in ('ok', 'partial')
assert 'items' in r.get('data', {})
n_prices = len(r['data']['items'])
print(f'[PASS] _dispatch("prices/latest") OK — {n_prices} items')

# Test 10: Dispatch weather/latest
r = _dispatch('weather/latest', {})
assert r['status'] in ('ok', 'partial')
assert 'items' in r.get('data', {})
n_weather = len(r['data']['items'])
print(f'[PASS] _dispatch("weather/latest") OK — {n_weather} items')

# Test 11: Dispatch intelligence/weather-price
r = _dispatch('intelligence/weather-price', {})
assert r['status'] in ('ok', 'partial')
assert 'items' in r.get('data', {})
n_wp = len(r['data']['items'])
print(f'[PASS] _dispatch("intelligence/weather-price") OK — {n_wp} items')

# Test 12: Dispatch intelligence/opportunities
r = _dispatch('intelligence/opportunities', {})
assert r['status'] == 'ok'
print(f'[PASS] _dispatch("intelligence/opportunities") OK — {len(r["data"]["opportunities"])} opps')

# Test 13: Dispatch sources/status
r = _dispatch('sources/status', {})
assert r['status'] == 'ok'
assert 'sources' in r['data']
print(f'[PASS] _dispatch("sources/status") OK')

# Test 14: Dispatch pipeline/status
r = _dispatch('pipeline/status', {})
assert r['status'] == 'ok'
print(f'[PASS] _dispatch("pipeline/status") OK')

# Test 15: Dispatch pipeline/freshness
r = _dispatch('pipeline/freshness', {})
assert r['status'] == 'ok'
print(f'[PASS] _dispatch("pipeline/freshness") OK')

# Test 16: Dispatch pipeline/runs
r = _dispatch('pipeline/runs', {})
assert r['status'] == 'ok'
assert 'runs' in r['data']
print(f'[PASS] _dispatch("pipeline/runs") OK')

# Test 17: Dispatch weather/risk
r = _dispatch('weather/risk', {})
assert r['status'] == 'ok'
assert 'events' in r['data']
print(f'[PASS] _dispatch("weather/risk") OK')

# Test 18: Dispatch report/daily
r = _dispatch('report/daily', {})
assert r['status'] == 'ok'
print(f'[PASS] _dispatch("report/daily") OK')

# Test 19: Dispatch prices/history
r = _dispatch('prices/history', {'product': ['tomate'], 'limit': ['5']})
assert r['status'] in ('ok', 'partial')
print(f'[PASS] _dispatch("prices/history") OK — {len(r["data"]["items"])} items')

# Test 20: Dispatch intelligence/predictions
r = _dispatch('intelligence/predictions', {})
assert r['status'] == 'ok'
print(f'[PASS] _dispatch("intelligence/predictions") OK')

# Test 21: Dispatch intelligence/alerts
r = _dispatch('intelligence/alerts', {})
assert r['status'] == 'ok'
print(f'[PASS] _dispatch("intelligence/alerts") OK')

print(f'\n=== 21/21 testes NIAS API Core (unit) passaram! ===')
