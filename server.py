import http.server, urllib.request, urllib.parse, json, os, re, time, base64, threading

try:
    from curl_cffi import requests as _cf_requests
    _cf_session = _cf_requests.Session(impersonate="chrome120")
except ImportError:
    _cf_session = None

try:
    from bs4 import BeautifulSoup as _BS
except ImportError:
    _BS = None

PORT = int(os.environ.get('PORT', 8080))
DIR = os.path.dirname(os.path.abspath(__file__))

_cepea_cache = {}
_cepea_ttl = 900

def _fetch_cepea():
    if _cepea_cache.get('data') and time.time() - _cepea_cache.get('ts', 0) < _cepea_ttl:
        return _cepea_cache['data']
    indicators = {
        'soja':   {'url': 'https://cepea.org.br/br/indicador/soja.aspx',        'unit': 'R$/sc 60kg'},
        'milho':  {'url': 'https://cepea.org.br/br/indicador/milho.aspx',       'unit': 'R$/sc 60kg'},
        'boi':    {'url': 'https://cepea.org.br/br/indicador/boi-gordo.aspx',   'unit': 'R$/@'},
        'cafe':   {'url': 'https://cepea.org.br/br/indicador/cafe.aspx',        'unit': 'R$/sc 60kg'},
        'laranja':{'url': 'https://cepea.org.br/br/indicador/citros.aspx',      'unit': 'R$/cx 40.8kg'},
        'tomate': {'url': 'https://cepea.org.br/br/indicador/tomate.aspx',      'unit': 'R$/cx 25kg'},
        'batata': {'url': 'https://cepea.org.br/br/indicador/batata.aspx',      'unit': 'R$/sc 50kg'},
    }
    result = {}
    hdrs = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
    }
    for key, info in indicators.items():
        try:
            html = None
            if _cf_session:
                r = _cf_session.get(info['url'], headers=hdrs, timeout=15)
                if r.status_code == 200:
                    html = r.text
            if not html:
                req = urllib.request.Request(info['url'], headers=hdrs)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    html = resp.read().decode('utf-8', errors='ignore')
            if not html:
                continue
            price_val = None
            change_val = 0
            date_str = time.strftime('%Y-%m-%d')
            if _BS:
                soup = _BS(html, 'html.parser')
                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')
                    if len(rows) >= 2:
                        cells = [td.get_text(strip=True) for td in rows[1].find_all('td')]
                        if len(cells) >= 3:
                            date_str = cells[0]
                            price_str = cells[1].replace('.', '').replace(',', '.')
                            price_val = float(price_str)
                            chg = cells[2].replace(',', '.').replace('%', '').strip()
                            change_val = float(chg)
            if price_val is None:
                td_vals = re.findall(r'<td[^>]*>\s*([\d.,]+)\s*</td>', html)
                changes = re.findall(r'([+-]?\d+[.,]\d+)\s*%', html)
                if td_vals:
                    price_str = td_vals[0].replace('.', '').replace(',', '.')
                    price_val = float(price_str)
                if changes:
                    change_val = float(changes[0].replace(',', '.'))
            if price_val:
                result[key] = {
                    'price': price_val,
                    'unit': info['unit'],
                    'change': change_val,
                    'source': 'CEPEA/ESALQ',
                    'date': date_str,
                }
        except Exception:
            pass
    if result:
        _cepea_cache['data'] = result
        _cepea_cache['ts'] = time.time()
    return result

# ── CONAB PROHORT + Preços Semanais — Dados reais massivos ─────────
_conab_cache = {}

def _fetch_conab():
    if _conab_cache.get('data') and time.time() - _conab_cache.get('ts', 0) < 3600:
        return _conab_cache['data']
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    result = {'hortifruti': {}, 'agro': {}, 'meta': {}}

    # Strategy 1: PrecosSemanalUF (17MB — 130+ produtos, todas UFs, semanal ATUALIZADO)
    try:
        req = urllib.request.Request(
            'https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosSemanalUF.txt',
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode('latin-1', errors='ignore')
        lines = raw.strip().split('\n')
        result['meta']['semanal_uf_lines'] = len(lines)
        result['meta']['source'] = 'CONAB/PrecosSemanalUF'
        # Parse: produto;classificao;id;uf;regiao;ano;mes;data_semana;semana;nivel;valor
        latest = {}
        for line in lines[1:]:
            cols = [c.strip() for c in line.split(';')]
            if len(cols) < 11: continue
            prod = cols[0].strip()
            uf = cols[3].strip()
            data_sem = cols[7].strip()
            valor_str = cols[10].strip().replace(',', '.')
            try:
                valor = float(valor_str)
            except ValueError:
                continue
            if valor <= 0: continue
            key = prod
            if key not in latest or data_sem > latest[key].get('_date', ''):
                latest[key] = {'_date': data_sem, 'prices': {}}
            if uf not in latest[key]['prices'] or data_sem >= latest[key].get('_date', ''):
                latest[key]['prices'][uf] = {'value': valor, 'date': data_sem, 'uf': uf}

        for prod, info in latest.items():
            if not info['prices']: continue
            vals = [p['value'] for p in info['prices'].values()]
            avg = sum(vals) / len(vals)
            result['agro'][prod] = {
                'avg_price': round(avg, 2),
                'min_price': round(min(vals), 2),
                'max_price': round(max(vals), 2),
                'uf_count': len(info['prices']),
                'date': info['_date'],
                'unit': 'R$/kg',
                'source': 'CONAB Semanal UF',
                'by_uf': {uf: d['value'] for uf, d in list(info['prices'].items())[:10]}
            }
    except Exception as e:
        result['meta']['semanal_error'] = str(e)

    # Strategy 2: ProhortDiario (167MB — CEASA diário, mais lento)
    # Skip if semanal succeeded (to avoid timeout)
    if not result['agro']:
        try:
            req = urllib.request.Request(
                'https://portaldeinformacoes.conab.gov.br/downloads/arquivos/ProhortDiario.txt',
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode('latin-1', errors='ignore')
            lines = raw.strip().split('\n')
            result['meta']['prohort_lines'] = len(lines)
            # Parse last 5000 lines (most recent)
            for line in lines[-5000:]:
                cols = [c.strip() for c in line.split(';')]
                if len(cols) < 8: continue
                ceasa = cols[3].strip()
                prod = cols[4].strip()
                data = cols[6].strip()[:10]
                try: preco = float(cols[7].strip().replace(',', '.'))
                except: continue
                if preco <= 0: continue
                if prod not in result['hortifruti']:
                    result['hortifruti'][prod] = {'ceasas': [], 'source': 'CONAB/PROHORT Diário'}
                result['hortifruti'][prod]['ceasas'].append({'ceasa': ceasa, 'price': preco, 'date': data})
            for prod in result['hortifruti']:
                prices = [c['price'] for c in result['hortifruti'][prod]['ceasas']]
                result['hortifruti'][prod]['avg'] = round(sum(prices)/len(prices), 2) if prices else 0
                result['hortifruti'][prod]['count'] = len(prices)
        except Exception as e:
            result['meta']['prohort_error'] = str(e)

    if result['agro'] or result['hortifruti']:
        result['meta']['updated'] = time.strftime('%Y-%m-%d %H:%M')
        _conab_cache['data'] = result
        _conab_cache['ts'] = time.time()
    return result

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DIR, **kw)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path.startswith('/api/flv/'):
            from flv.api.routes import handle_flv
            handle_flv(self, self.path)
            return
        if self.path.startswith('/proxy/'):
            self._proxy('POST')
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path.startswith('/api/flv/'):
            from flv.api.routes import handle_flv
            handle_flv(self, self.path)
            return
        if self.path == '/api/ceagesp':
            self._serve_ceagesp()
            return
        if self.path == '/api/rodovias':
            self._serve_rodovias()
            return
        if self.path.startswith('/proxy/'):
            self._proxy('GET')
        elif self.path == '/api/cepea':
            self._serve_cepea()
        elif self.path == '/api/conab':
            self._serve_conab()
        else:
            super().do_GET()

    def _serve_cepea(self):
        data = _fetch_cepea()
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _serve_conab(self):
        data = _fetch_conab()
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _serve_ceagesp(self):
        from flv.collectors.ceagesp_live import fetch_ceagesp
        data = fetch_ceagesp()
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _serve_rodovias(self):
        from flv.collectors.rodovias import fetch_rodovias_status
        data = fetch_rodovias_status()
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    def _proxy(self, method):
        target = self.path[7:]  # strip /proxy/
        target = 'https://' + target if not target.startswith('http') else target
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length > 0 else None
        headers = {}
        for h in ('Authorization', 'Content-Type'):
            if self.headers.get(h):
                headers[h] = self.headers[h]
        try:
            req = urllib.request.Request(target, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                self.send_response(resp.status)
                self._cors()
                ct = resp.headers.get('Content-Type', 'application/json')
                self.send_header('Content-Type', ct)
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

print(f'NIA$ server on http://localhost:{PORT}')

# Initialize FLV module
try:
    from flv.db import init_db
    init_db()

    def _flv_scheduler():
        time.sleep(10)  # Wait for server startup
        from flv.pipeline import run_pipeline
        run_pipeline()
        while True:
            time.sleep(6 * 3600)
            try:
                run_pipeline()
            except Exception as e:
                print(f'[FLV-Scheduler] Erro: {e}')

    threading.Thread(target=_flv_scheduler, daemon=True).start()

    def _flv_alert_watchdog():
        time.sleep(60)  # Initial delay
        while True:
            try:
                from flv.model.thresholds import evaluate_realtime
                evaluate_realtime()
            except Exception as e:
                print(f'[FLV-Watchdog] Erro: {e}')
            time.sleep(1800)

    threading.Thread(target=_flv_alert_watchdog, daemon=True).start()
    print('[FLV] Pipeline e watchdog iniciados')
except Exception as e:
    print(f'[FLV] Init warning: {e}')

http.server.HTTPServer(('', PORT), ProxyHandler).serve_forever()
