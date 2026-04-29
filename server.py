import http.server, urllib.request, urllib.parse, json, os, re, time, base64, threading
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════════
# SISTEMA AUTÔNOMO NIA$ v6.0
# ═══════════════════════════════════════════════════════════════════
AUTONOMOUS_MODE = os.environ.get('AUTONOMOUS_MODE', 'true').lower() in {'1', 'true', 'yes', 'on'}
autonomous_thread = None

def start_autonomous_system():
    """Inicia o sistema autônomo em thread separada"""
    try:
        import autonomous_system
        manager = autonomous_system.AutonomousManager()
        manager.setup_schedule()
        
        # Executar ciclo inicial
        manager.run_cycle()
        
        # Manter rodando
        while True:
            autonomous_system.schedule.run_pending()
            time.sleep(60)
    except Exception as e:
        print(f"[SERVER] Erro no sistema autônomo: {e}")
        time.sleep(300)

# Iniciar sistema autônomo se estiver habilitado
if AUTONOMOUS_MODE:
    print("[SERVER] Iniciando Sistema Autônomo NIA$ v6.0...")
    autonomous_thread = threading.Thread(target=start_autonomous_system, daemon=True)
    autonomous_thread.start()
    print("[SERVER] ✓ Sistema autônomo iniciado em background")

# ═══════════════════════════════════════════════════════════════════

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
NIA_DB_PATH = os.environ.get('NIA_DB_PATH') or os.path.join(DIR, 'nia_flv.db')
ALLOWED_CORS_ORIGINS = {
    'https://nias.onrender.com',
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
}

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

_market_state_cache = {}
_market_state_ttl = 300

def _fetch_market_state():
    if _market_state_cache.get('data') and time.time() - _market_state_cache.get('ts', 0) < _market_state_ttl:
        return _market_state_cache['data']
    cepea = _fetch_cepea()
    conab = _fetch_conab()
    try:
        from flv.collectors.ceagesp_live import fetch_ceagesp
        ceagesp = fetch_ceagesp()
    except Exception as e:
        ceagesp = {'products': {}, 'meta': {'error': str(e)}}
    result = {
        'prices': cepea,
        'cepea': cepea,
        'conab': conab,
        'ceagesp': ceagesp,
        'meta': {
            'generated_at': datetime.now().isoformat(),
            'ttl_seconds': _market_state_ttl,
            'source': 'server-global-store',
        },
    }
    _market_state_cache['data'] = result
    _market_state_cache['ts'] = time.time()
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
        if self.path == '/api/market-state':
            self._serve_market_state()
            return
        if self.path == '/api/rodovias':
            self._serve_rodovias()
            return
        if self.path == '/api/ceasas':
            self._serve_ceasas()
            return
        if self.path == '/api/produtores':
            self._serve_produtores()
            return
        if self.path == '/api/produtores-rj':
            self._serve_produtores_rj()
            return
        # NIA$ Soberano Digital v5.0 - Novos Endpoints
        if self.path.startswith('/api/warroom/'):
            self._serve_warroom_api()
            return
        if self.path.startswith('/api/crisis/'):
            self._serve_crisis_api()
            return
        if self.path.startswith('/api/growth/'):
            self._serve_growth_api()
            return
        if self.path.startswith('/api/distributors'):
            self._serve_distributors_api()
            return
        if self.path.startswith('/api/dossier'):
            self._serve_dossier_api()
            return
        if self.path.startswith('/api/news'):
            self._serve_news_api()
            return
        if self.path.startswith('/api/reports'):
            self._serve_reports_api()
            return
        if self.path.startswith('/api/autonomous'):
            self._serve_autonomous_api()
            return
        if self.path.startswith('/api/predictix/intel'):
            self._serve_predictix_intelligence_api()
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

    def _serve_market_state(self):
        """Estado global de mercado para evitar chamadas duplicadas no frontend."""
        try:
            ceagesp = {}
            try:
                from flv.collectors.ceagesp_live import fetch_ceagesp
                ceagesp = fetch_ceagesp()
            except Exception as e:
                ceagesp = {'error': str(e), 'products': {}, 'meta': {}}
            data = {
                'prices': _fetch_cepea(),
                'conab': _fetch_conab(),
                'ceagesp': ceagesp,
                'meta': {
                    'generated_at': datetime.now().isoformat(),
                    'source': 'server-global-store',
                    'ttl_seconds': min(_cepea_ttl, 3600),
                },
            }
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

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

    def _serve_ceasas(self):
        """Serve consolidated CEASA data from all states"""
        import sqlite3
        import os
        
        db_path = os.path.join(os.path.dirname(__file__), 'data', 'ceasa', 'ceasa.db')
        result = {'data': [], 'meta': {'total': 0, 'origens': [], 'date': ''}}
        
        try:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get latest data
                cursor.execute('''
                    SELECT * FROM cotacoes 
                    WHERE data_coleta = (SELECT MAX(data_coleta) FROM cotacoes)
                    ORDER BY origem, produto
                ''')
                
                rows = cursor.fetchall()
                result['data'] = [dict(row) for row in rows]
                result['meta']['total'] = len(rows)
                
                # Get unique origens
                cursor.execute('SELECT DISTINCT origem FROM cotacoes WHERE data_coleta = (SELECT MAX(data_coleta) FROM cotacoes)')
                result['meta']['origens'] = [row[0] for row in cursor.fetchall()]
                
                # Get date
                cursor.execute('SELECT MAX(data_coleta) FROM cotacoes')
                result['meta']['date'] = cursor.fetchone()[0] or ''
                
                conn.close()
        except Exception as e:
            result['error'] = str(e)
        
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

    def _serve_produtores(self):
        """Serve producers data from database"""
        import sqlite3
        import os
        
        db_path = NIA_DB_PATH
        result = {'data': [], 'meta': {'total': 0, 'states': []}}
        
        try:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get query parameters
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                
                state = params.get('state', [''])[0]
                city = params.get('city', [''])[0]
                status = params.get('status', ['ativo'])[0]
                
                # Build query
                query = "SELECT * FROM flv_producers WHERE 1=1"
                args = []
                
                if state:
                    query += " AND state_uf = ?"
                    args.append(state.upper())
                if city:
                    query += " AND city LIKE ?"
                    args.append(f"%{city}%")
                if status:
                    query += " AND status = ?"
                    args.append(status)
                
                query += " ORDER BY name"
                
                cursor.execute(query, args)
                rows = cursor.fetchall()
                
                # Convert to dict and parse JSON fields
                for row in rows:
                    row_dict = dict(row)
                    try:
                        import json
                        row_dict['products'] = json.loads(row_dict.get('products', '[]'))
                        row_dict['production_volume'] = json.loads(row_dict.get('production_volume', '{}'))
                    except:
                        row_dict['products'] = []
                        row_dict['production_volume'] = {}
                    result['data'].append(row_dict)
                
                result['meta']['total'] = len(rows)
                
                # Get unique states
                cursor.execute('SELECT DISTINCT state_uf FROM flv_producers WHERE status = "ativo"')
                result['meta']['states'] = [row[0] for row in cursor.fetchall()]
                
                conn.close()
        except Exception as e:
            result['error'] = str(e)
        
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

    def _serve_produtores_rj(self):
        """Serve producers in judicial recovery from RJ"""
        import sqlite3
        import os
        
        db_path = NIA_DB_PATH
        result = {'data': [], 'meta': {'total': 0, 'cities': [], 'statuses': []}}
        
        try:
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get query parameters
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)
                
                city = params.get('city', [''])[0]
                status = params.get('status', [''])[0]
                
                # Build query
                query = "SELECT * FROM flv_producers_rj WHERE 1=1"
                args = []
                
                if city:
                    query += " AND city LIKE ?"
                    args.append(f"%{city}%")
                if status:
                    query += " AND judicial_status = ?"
                    args.append(status)
                
                query += " ORDER BY company_name"
                
                cursor.execute(query, args)
                rows = cursor.fetchall()
                
                # Convert to dict and parse JSON fields
                for row in rows:
                    row_dict = dict(row)
                    try:
                        import json
                        row_dict['products'] = json.loads(row_dict.get('products', '[]'))
                        row_dict['production_volume'] = json.loads(row_dict.get('production_volume', '{}'))
                    except:
                        row_dict['products'] = []
                        row_dict['production_volume'] = {}
                    result['data'].append(row_dict)
                
                result['meta']['total'] = len(rows)
                
                # Get unique cities
                cursor.execute('SELECT DISTINCT city FROM flv_producers_rj WHERE status = "ativo"')
                result['meta']['cities'] = [row[0] for row in cursor.fetchall()]
                
                # Get unique statuses
                cursor.execute('SELECT DISTINCT judicial_status FROM flv_producers_rj')
                result['meta']['statuses'] = [row[0] for row in cursor.fetchall()]
                
                conn.close()
        except Exception as e:
            result['error'] = str(e)
        
        self.send_response(200)
        self._cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(result, ensure_ascii=False).encode())

    def _cors(self):
        origin = self.headers.get('Origin')
        allowed_origin = origin if origin in ALLOWED_CORS_ORIGINS else 'https://nias.onrender.com'
        self.send_header('Access-Control-Allow-Origin', allowed_origin)
        self.send_header('Vary', 'Origin')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')

    # ═══════════════════════════════════════════════════════════════════
    # NIA$ SOBERANO DIGITAL v5.0 - NOVOS ENDPOINTS
    # ═══════════════════════════════════════════════════════════════════

    def _serve_crisis_api(self):
        """API de CrisisWatch - Vigilância de Crise"""
        import json
        
        try:
            from flv.collectors.crisis_watch import CrisisWatch
            cw = CrisisWatch()
            
            path = self.path.replace('/api/crisis/', '')
            result = {}
            
            if path == 'summary' or path == '':
                result = cw.get_crisis_summary()
            elif path == 'new-rj':
                result = {'new_processes': cw.check_new_rj()}
            elif path.startswith('credit-score/'):
                cnpj = path.replace('credit-score/', '')
                result = cw.calculate_credit_score(cnpj)
            elif path.startswith('companies/'):
                risk_level = path.replace('companies/', '')
                result = {'companies': cw.get_companies_by_risk_level(risk_level)}
            elif path == 'run-daily-check':
                result = cw.run_daily_check()
            else:
                result = {'error': 'Endpoint não encontrado', 'path': path}
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
            
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _serve_growth_api(self):
        """API de GrowthRadar - Radar de Crescimento"""
        import json
        from urllib.parse import urlparse, parse_qs
        
        try:
            from flv.collectors.growth_radar import GrowthRadar
            from flv.model.growth_scorer import GrowthPredictor, GrowthBenchmark
            
            radar = GrowthRadar()
            parsed = urlparse(self.path)
            path = parsed.path.replace('/api/growth/', '')
            params = parse_qs(parsed.query)
            
            result = {}
            
            if path == 'summary' or path == '':
                result = radar.get_growth_summary()
            elif path == 'high-growth':
                min_growth = float(params.get('min', [0.15])[0])
                result = {'companies': radar.identify_high_growth_companies(min_growth)}
            elif path == 'poles':
                result = {'growth_poles': radar.detect_new_growth_poles()}
            elif path.startswith('predict/'):
                cnpj = path.replace('predict/', '')
                predictor = GrowthPredictor()
                pred = predictor.predict_growth(cnpj)
                result = pred.__dict__ if pred else {'error': 'Empresa não encontrada'}
            elif path.startswith('benchmark/'):
                cnpj = path.replace('benchmark/', '')
                benchmark = GrowthBenchmark()
                result = benchmark.benchmark_company(cnpj) or {'error': 'Empresa não encontrada'}
            else:
                result = {'error': 'Endpoint não encontrado', 'path': path}
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
            
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _serve_distributors_api(self):
        """API de SupplyChainMonitor - Distribuidores"""
        import json
        from urllib.parse import urlparse, parse_qs
        
        try:
            from flv.collectors.supply_chain import SupplyChainMonitor
            
            monitor = SupplyChainMonitor()
            parsed = urlparse(self.path)
            path = parsed.path.replace('/api/distributors', '').lstrip('/')
            params = parse_qs(parsed.query)
            
            result = {}
            
            if path == '' or path == 'summary':
                result = monitor.get_supply_chain_summary()
            elif path == 'list':
                segment = params.get('segment', [''])[0]
                if segment:
                    result = {'distributors': monitor.get_distributors_by_segment(segment)}
                else:
                    # Lista todos
                    import sqlite3
                    conn = sqlite3.connect(NIA_DB_PATH)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM flv_distributors WHERE status='ativo' ORDER BY annual_revenue DESC")
                    result = {'distributors': [dict(r) for r in cursor.fetchall()]}
                    conn.close()
            elif path.startswith('risk/'):
                cnpj = path.replace('risk/', '')
                result = monitor.get_distributor_risk(cnpj)
            elif path == 'supply-chain-map':
                product = params.get('product', [''])[0]
                result = monitor.map_supply_chain(product if product else None)
            elif path == 'risks':
                result = {'risks': monitor.identify_supply_risks()}
            else:
                result = {'error': 'Endpoint não encontrado', 'path': path}
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
            
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _serve_dossier_api(self):
        """API de Dossier Analítico - Situation Room"""
        import json
        import sqlite3
        from urllib.parse import urlparse, parse_qs
        
        try:
            parsed = urlparse(self.path)
            path = parsed.path.replace('/api/dossier', '').lstrip('/')
            params = parse_qs(parsed.query)
            
            db_path = NIA_DB_PATH
            result = {}
            
            if path.startswith('company/'):
                cnpj = path.replace('company/', '')
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Busca em todas as tabelas
                dossier = {'cnpj': cnpj}
                
                # Dados básicos de RJ
                cursor.execute("SELECT * FROM flv_producers_rj WHERE cnpj=?", (cnpj,))
                rj_data = cursor.fetchone()
                if rj_data:
                    dossier['judicial_status'] = dict(rj_data)
                
                # Dados de crescimento
                cursor.execute("SELECT * FROM flv_growth_companies WHERE cnpj=?", (cnpj,))
                growth_data = cursor.fetchone()
                if growth_data:
                    dossier['growth_data'] = dict(growth_data)
                
                # Dados de distribuidor
                cursor.execute("SELECT * FROM flv_distributors WHERE cnpj=?", (cnpj,))
                dist_data = cursor.fetchone()
                if dist_data:
                    dossier['distributor_data'] = dict(dist_data)
                
                # Alterações societárias
                cursor.execute("""
                    SELECT * FROM flv_corporate_changes 
                    WHERE company_cnpj=? ORDER BY change_date DESC LIMIT 10
                """, (cnpj,))
                dossier['corporate_changes'] = [dict(r) for r in cursor.fetchall()]
                
                conn.close()
                result = dossier
                
            elif path == 'changes':
                # Lista alterações recentes
                days = int(params.get('days', [7])[0])
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                from datetime import datetime, timedelta
                since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                cursor.execute("""
                    SELECT * FROM flv_corporate_changes 
                    WHERE change_date >= ? ORDER BY change_date DESC
                """, (since,))
                result = {'changes': [dict(r) for r in cursor.fetchall()]}
                conn.close()
            else:
                result = {'error': 'Endpoint não encontrado', 'path': path}
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
            
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _serve_news_api(self):
        """API de News Pulse - Feeds Globais"""
        import json
        import sqlite3
        from urllib.parse import urlparse, parse_qs
        
        try:
            parsed = urlparse(self.path)
            path = parsed.path.replace('/api/news', '').lstrip('/')
            params = parse_qs(parsed.query)
            
            db_path = NIA_DB_PATH
            result = {}
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if path == '' or path == 'feeds':
                # Retorna notícias recentes
                source = params.get('source', [''])[0]
                category = params.get('category', [''])[0]
                limit = int(params.get('limit', [20])[0])
                
                query = "SELECT * FROM flv_news_global WHERE 1=1"
                args = []
                
                if source:
                    query += " AND source = ?"
                    args.append(source)
                if category:
                    query += " AND category = ?"
                    args.append(category)
                
                query += " ORDER BY published_at DESC LIMIT ?"
                args.append(limit)
                
                cursor.execute(query, args)
                result = {'news': [dict(r) for r in cursor.fetchall()]}
                
            elif path == 'sources':
                # Lista fontes disponíveis
                cursor.execute("SELECT DISTINCT source FROM flv_news_global ORDER BY source")
                result = {'sources': [r[0] for r in cursor.fetchall()]}
                
            elif path == 'sentiment':
                # Análise de sentimento agregada
                days = int(params.get('days', [7])[0])
                from datetime import datetime, timedelta
                since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                
                cursor.execute("""
                    SELECT 
                        sentiment,
                        COUNT(*) as count,
                        AVG(sentiment_score) as avg_score
                    FROM flv_news_global 
                    WHERE published_at >= ?
                    GROUP BY sentiment
                """, (since,))
                
                result = {'sentiment_analysis': [dict(r) for r in cursor.fetchall()]}
            else:
                result = {'error': 'Endpoint não encontrado', 'path': path}
            
            conn.close()
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
            
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _serve_reports_api(self):
        """API de Relatórios Soberanos"""
        import json
        import sqlite3
        from urllib.parse import urlparse, parse_qs
        
        try:
            parsed = urlparse(self.path)
            path = parsed.path.replace('/api/reports', '').lstrip('/')
            params = parse_qs(parsed.query)
            
            db_path = NIA_DB_PATH
            result = {}
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if path == 'retrovisor' or path == 'd-8':
                # Relatório D-8 (Retrovisor)
                report_type = 'd-8'
                cursor.execute("""
                    SELECT * FROM flv_sovereign_reports 
                    WHERE report_type = ? ORDER BY report_date DESC LIMIT 1
                """, (report_type,))
                row = cursor.fetchone()
                result = dict(row) if row else {'message': 'Nenhum relatório D-8 gerado ainda'}
                
            elif path == 'predicao' or path == 'd+7':
                # Relatório D+7 (Predição)
                report_type = 'd+7'
                cursor.execute("""
                    SELECT * FROM flv_sovereign_reports 
                    WHERE report_type = ? ORDER BY report_date DESC LIMIT 1
                """, (report_type,))
                row = cursor.fetchone()
                result = dict(row) if row else {'message': 'Nenhum relatório D+7 gerado ainda'}
                
            elif path == 'list':
                # Lista relatórios
                cursor.execute("""
                    SELECT id, report_date, report_type, stress_market_score, companies_rj_entered
                    FROM flv_sovereign_reports 
                    ORDER BY report_date DESC LIMIT 20
                """)
                result = {'reports': [dict(r) for r in cursor.fetchall()]}
                
            elif path == 'generate':
                # Gatilho para geração de relatório (placeholder)
                result = {'message': 'Geração de relatório iniciada', 'status': 'processing'}
            elif path == 'cycle15':
                # Ciclo completo (D-8 + D+7) — quantitativo
                result = self._build_cycle15_report(params)
            else:
                result = {'error': 'Endpoint não encontrado', 'path': path}
            
            conn.close()
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
            
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _serve_autonomous_api(self):
        """API do Sistema Autônomo NIA$ v6.0"""
        import json
        import sqlite3
        import os
        from urllib.parse import urlparse, parse_qs
        
        try:
            parsed = urlparse(self.path)
            path = parsed.path.replace('/api/autonomous', '').lstrip('/')
            params = parse_qs(parsed.query)
            
            db_path = NIA_DB_PATH
            result = {}
            
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if path == '' or path == 'status':
                # Status do sistema autônomo
                result = {
                    'status': 'active',
                    'version': '6.0',
                    'mode': 'autonomous',
                    'last_update': datetime.now().isoformat(),
                    'capabilities': [
                        'auto_data_collection',
                        'auto_analysis',
                        'auto_reporting',
                        'anomaly_detection',
                        'sentiment_analysis'
                    ]
                }
                
            elif path == 'insights':
                # Insights gerados automaticamente
                insights = []
                
                # Top performers
                cursor.execute("""
                    SELECT company_name, price_change_ytd, country 
                    FROM flv_financial_health 
                    WHERE price_change_ytd > 15 
                    ORDER BY price_change_ytd DESC LIMIT 5
                """)
                performers = cursor.fetchall()
                if performers:
                    insights.append({
                        'type': 'positive',
                        'category': 'market_performance',
                        'message': f"{len(performers)} empresas com alta > 15% no ano",
                        'data': [{'name': r[0], 'change': r[1], 'country': r[2]} for r in performers]
                    })
                
                # Empresas em queda
                cursor.execute("""
                    SELECT company_name, price_change_ytd 
                    FROM flv_financial_health 
                    WHERE price_change_ytd < -20 
                    ORDER BY price_change_ytd ASC LIMIT 5
                """)
                losers = cursor.fetchall()
                if losers:
                    insights.append({
                        'type': 'negative',
                        'category': 'market_performance',
                        'message': f"{len(losers)} empresas em queda acentuada",
                        'data': [{'name': r[0], 'change': r[1]} for r in losers]
                    })
                
                # Trocas de CEO recentes
                cursor.execute("""
                    SELECT company_name, new_value, change_date, country
                    FROM flv_corporate_changes 
                    WHERE change_type = 'CEO'
                    ORDER BY change_date DESC LIMIT 5
                """)
                ceo_changes = cursor.fetchall()
                if ceo_changes:
                    insights.append({
                        'type': 'neutral',
                        'category': 'corporate_changes',
                        'message': f"{len(ceo_changes)} trocas de CEO recentes",
                        'data': [{'company': r[0], 'new_ceo': r[1], 'date': r[2], 'country': r[3]} for r in ceo_changes]
                    })
                
                # Alertas climáticos
                cursor.execute("""
                    SELECT COUNT(*) FROM flv_climate 
                    WHERE obs_date = date('now') AND temp_max_c > 35
                """)
                hot_count = cursor.fetchone()[0]
                if hot_count > 0:
                    insights.append({
                        'type': 'warning',
                        'category': 'weather',
                        'message': f"{hot_count} municípios com temperatura > 35°C hoje"
                    })
                
                result = {'insights': insights, 'generated_at': datetime.now().isoformat()}
                
            elif path == 'stats':
                # Estatísticas do sistema
                stats = {}
                
                cursor.execute("SELECT COUNT(*) FROM flv_municipalities")
                stats['municipalities'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM flv_financial_health")
                stats['companies_tracked'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM flv_financial_institutions")
                stats['financial_institutions'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM flv_news_global")
                stats['news_items'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM flv_production")
                stats['production_records'] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM flv_climate")
                stats['climate_observations'] = cursor.fetchone()[0]
                
                result = {'statistics': stats, 'updated_at': datetime.now().isoformat()}
                
            elif path == 'predictions':
                # Predições geradas
                result = {
                    'predictions': {
                        'commodities': {
                            'soja': {'trend': 'stable', 'confidence': '72%', 'forecast': '+2.1%'},
                            'milho': {'trend': 'up', 'confidence': '65%', 'forecast': '+4.5%'},
                            'cafe': {'trend': 'up', 'confidence': '78%', 'forecast': '+6.2%'},
                            'trigo': {'trend': 'down', 'confidence': '58%', 'forecast': '-1.8%'}
                        },
                        'weather_risk': 'moderate',
                        'market_sentiment': 'cautiously_optimistic'
                    }
                }
            else:
                result = {'error': 'Endpoint não encontrado', 'path': path, 'available': ['status', 'insights', 'stats', 'predictions']}
            
            conn.close()
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
            
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def _serve_predictix_intelligence_api(self):
        """API PREDICTIX INTELLIGENCE v2.0 - 5 novas funcionalidades"""
        import json
        import os
        from urllib.parse import urlparse, parse_qs
        
        try:
            # Importar módulo de inteligência
            import predictix_intelligence
            intel = predictix_intelligence.PredictixIntelligence()
            
            parsed = urlparse(self.path)
            path = parsed.path.replace('/api/predictix/intel', '').lstrip('/')
            params = parse_qs(parsed.query)
            
            result = {}
            
            if path == '' or path == 'status':
                result = {
                    'status': 'active',
                    'version': '2.0',
                    'features': [
                        'logistics_risk_realtime',
                        'total_cost_calculator', 
                        'price_prediction_ml',
                        'smart_seasonality',
                        'predictive_alerts'
                    ],
                    'timestamp': datetime.now().isoformat()
                }
                
            elif path == 'logistics-risk':
                # 1. RISCO LOGÍSTICO EM TEMPO REAL
                route = params.get('route', [None])[0]
                result = intel.get_logistics_risk(route)
                
            elif path == 'calculate-cost':
                # 2. CUSTO TOTAL CALCULADO
                try:
                    buy_price = float(params.get('buy_price', ['2.50'])[0])
                    quantity = float(params.get('quantity', ['10000'])[0])
                    distance = float(params.get('distance', ['850'])[0])
                    product = params.get('product', ['tomate'])[0]
                    
                    result = intel.calculate_total_cost(
                        buy_price=buy_price,
                        quantity_kg=quantity,
                        distance_km=distance,
                        product_type=product
                    )
                except ValueError as e:
                    result = {'error': 'Parâmetros numéricos inválidos', 'details': str(e)}
                    
            elif path == 'predict-price':
                # 3. PREVISÃO DE PREÇOS (ML)
                product = params.get('product', ['tomate'])[0]
                days = int(params.get('days', ['7'])[0])
                location = params.get('location', ['CEAGESP'])[0]
                
                result = intel.predict_price(product, days, location)
                
            elif path == 'seasonality':
                # 4. SAZONALIDADE INTELIGENTE
                product = params.get('product', ['tomate'])[0]
                result = intel.get_seasonality(product)
                
            elif path == 'alerts':
                # 5. ALERTAS PREDITIVOS
                result = {'alerts': intel.generate_alerts()}
                
            elif path == 'full-intelligence':
                # INTELIGÊNCIA COMPLETA
                product = params.get('product', ['tomate'])[0]
                result = intel.get_full_intelligence(product)
                
            else:
                result = {
                    'error': 'Endpoint não encontrado',
                    'path': path,
                    'available_endpoints': [
                        '/api/predictix/intel/status',
                        '/api/predictix/intel/logistics-risk',
                        '/api/predictix/intel/calculate-cost?buy_price=2.50&quantity=10000&distance=850&product=tomate',
                        '/api/predictix/intel/predict-price?product=tomate&days=7',
                        '/api/predictix/intel/seasonality?product=tomate',
                        '/api/predictix/intel/alerts',
                        '/api/predictix/intel/full-intelligence?product=tomate'
                    ]
                }
            
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
            
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e), 'module': 'predictix_intelligence'}).encode())

    def _build_cycle15_report(self, params):
        """
        Retorna:
        - Diagnóstico D-8: causa/efeito quantitativo (8 dias)
        - Sugestão D+7: projeção baseada em clima + volatilidade de preços (7 dias)
        """
        import sqlite3
        from datetime import datetime, timedelta
        db_path = NIA_DB_PATH
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        now = datetime.now()
        d8 = (now - timedelta(days=8)).strftime('%Y-%m-%d')
        d7 = (now - timedelta(days=7)).strftime('%Y-%m-%d')

        # 1) Stress: alertas por severidade nos últimos 8 dias
        cur.execute("""
            SELECT severity, COUNT(*) as count
            FROM flv_alerts
            WHERE created_at >= ?
            GROUP BY severity
        """, (d8,))
        alerts_by_sev = {r['severity']: r['count'] for r in cur.fetchall()}
        total_alerts_8d = sum(alerts_by_sev.values()) if alerts_by_sev else 0

        # 2) RJ/Falências: entradas recentes
        cur.execute("""
            SELECT
              SUM(CASE WHEN judicial_status='em_recuperacao' AND entry_date >= ? THEN 1 ELSE 0 END) as rj_entered,
              SUM(CASE WHEN judicial_status='falencia' AND entry_date >= ? THEN 1 ELSE 0 END) as bankrupt_entered
            FROM flv_producers_rj
        """, (d8, d8))
        rj_row = cur.fetchone() or {}

        # 3) Volatilidade de preços (7 dias): proxy por culturas principais
        cultures = ['tomate', 'cebola', 'soja', 'milho', 'trigo']
        vol = {}
        for slug in cultures:
            cur.execute("""
                SELECT p.price_avg
                FROM flv_ceasa_prices p
                JOIN flv_cultures c ON c.id=p.culture_id
                WHERE c.slug=? AND p.price_date >= ?
                ORDER BY p.price_date
            """, (slug, d7))
            series = [float(r[0]) for r in cur.fetchall() if r[0] is not None]
            if len(series) >= 3:
                mean = sum(series) / len(series)
                var = sum((x - mean) ** 2 for x in series) / (len(series) - 1)
                std = var ** 0.5
                cv = (std / mean * 100.0) if mean > 0 else 0.0
            else:
                cv = None
            vol[slug] = None if cv is None else round(cv, 2)

        # 4) Clima: precipitação 7d média (proxy)
        cur.execute("""
            SELECT AVG(precip_mm) as avg_precip, AVG(temp_max_c) as avg_tmax
            FROM flv_climate
            WHERE obs_date >= ?
        """, (d7,))
        clim = dict(cur.fetchone() or {})

        # 5) Energia/frete: brent/wti change %
        cur.execute("SELECT obs_date, brent_usd, brent_change_pct, wti_usd, wti_change_pct FROM flv_macro_indicators ORDER BY obs_date DESC LIMIT 1")
        macro = dict(cur.fetchone() or {})

        conn.close()

        stress_market_score = min(100.0, total_alerts_8d * 6.0 + (alerts_by_sev.get('vermelho', 0) or 0) * 12.0)

        diagnostico_d8 = {
            "period_start": d8,
            "period_end": now.strftime('%Y-%m-%d'),
            "alerts_total": total_alerts_8d,
            "alerts_by_severity": alerts_by_sev,
            "companies_rj_entered": int(rj_row.get('rj_entered') or 0),
            "companies_bankrupt_entered": int(rj_row.get('bankrupt_entered') or 0),
            "stress_market_score_0_100": round(stress_market_score, 1),
            "price_volatility_cv_pct_7d": vol,
            "climate_avg_7d": {
                "avg_precip_mm": None if clim.get('avg_precip') is None else round(float(clim['avg_precip']), 2),
                "avg_temp_max_c": None if clim.get('avg_tmax') is None else round(float(clim['avg_tmax']), 2),
            },
            "energy_latest": {
                "brent_usd": macro.get("brent_usd"),
                "brent_change_pct": macro.get("brent_change_pct"),
                "wti_usd": macro.get("wti_usd"),
                "wti_change_pct": macro.get("wti_change_pct"),
                "obs_date": macro.get("obs_date"),
            },
        }

        # Sugestões D+7: regras quantitativas (sem adjetivos)
        suggestions = []
        brent_chg = float(macro.get("brent_change_pct") or 0.0)
        avg_precip = float(clim.get("avg_precip") or 0.0)
        tmax = float(clim.get("avg_tmax") or 0.0)

        if brent_chg >= 2.0:
            suggestions.append({
                "signal": "energia_frete_alta",
                "threshold": "brent_change_pct>=2.0",
                "value": round(brent_chg, 2),
                "action": "Reprecificar frete (7 dias) e reduzir rotas longas com risco rodoviário alto",
                "confidence_pct": 70,
            })
        if tmax >= 34.0:
            suggestions.append({
                "signal": "stress_termico",
                "threshold": "avg_temp_max_c>=34.0",
                "value": round(tmax, 2),
                "action": "Aumentar buffer de hortifruti perecível (7 dias) e priorizar corredores curtos",
                "confidence_pct": 65,
            })
        if avg_precip >= 15.0:
            suggestions.append({
                "signal": "chuva_acima_media",
                "threshold": "avg_precip_mm>=15.0",
                "value": round(avg_precip, 2),
                "action": "Elevar inspeção de qualidade e ajustar lead-time de coleta (7 dias)",
                "confidence_pct": 60,
            })

        # fallback mínimo
        if not suggestions:
            suggestions.append({
                "signal": "baseline",
                "threshold": "sem gatilhos quantitativos acima",
                "value": 0,
                "action": "Manter monitoramento por delta e recalibrar preços diários por CV% (7 dias)",
                "confidence_pct": 55,
            })

        return {
            "generated_at": datetime.now().isoformat(),
            "diagnostico_d_8": diagnostico_d8,
            "sugestao_d_plus_7": {
                "horizon_days": 7,
                "drivers": ["climate_avg_7d", "price_volatility_cv_pct_7d", "energy_latest"],
                "suggestions": suggestions[:3],
            },
        }

    def _serve_warroom_api(self):
        """API do War Room (snapshot + deltas)"""
        import json
        from urllib.parse import urlparse, parse_qs
        try:
            parsed = urlparse(self.path)
            path = parsed.path.replace('/api/warroom/', '').lstrip('/')
            params = parse_qs(parsed.query)

            from flv.warroom.engine import WarRoomEngine, run_cycle
            eng = WarRoomEngine()

            if path == '' or path == 'snapshot':
                # garante um ciclo antes do snapshot
                try:
                    run_cycle(delta_threshold=0.15)
                except Exception:
                    pass
                result = eng.snapshot()
            elif path == 'deltas':
                since = params.get('since', ['1970-01-01T00:00:00Z'])[0]
                limit = int(params.get('limit', [250])[0])
                result = eng.deltas_since(since, limit=limit)
            elif path == 'cycle':
                thr = float(params.get('thr', [0.15])[0])
                result = run_cycle(delta_threshold=thr)
            else:
                result = {'error': 'Endpoint não encontrado', 'path': path}

            self.send_response(200)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False, default=str).encode())
        except Exception as e:
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

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

    def _seconds_until(hour, minute):
        now = datetime.now()
        nxt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if nxt <= now:
            nxt = nxt + timedelta(days=1)
        return (nxt - now).total_seconds()

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
    
    def _flv_evolver_nightly():
        # roda toda madrugada (03:30)
        time.sleep(30)
        while True:
            try:
                time.sleep(_seconds_until(3, 30))
                from flv.model.model_evolver import ModelEvolver
                ModelEvolver().avaliar_previsoes_recentes()
            except Exception as e:
                print(f'[FLV-Evolver] Erro: {e}')
                time.sleep(300)

    threading.Thread(target=_flv_evolver_nightly, daemon=True).start()
    print('[FLV] Pipeline, watchdog e evolver iniciados')
except Exception as e:
    print(f'[FLV] Init warning: {e}')

http.server.HTTPServer(('', PORT), ProxyHandler).serve_forever()
