"""NIAS - Memory API: memória de mercado com busca TF-IDF simplificada."""
import json
import re
import math
from datetime import datetime, timezone
from urllib.parse import parse_qs

from flv.db import get_conn

# Stopwords PT-BR básicas
_STOPWORDS = {
    'a','ao','aos','as','com','da','das','de','do','dos','e','em',
    'é','era','essa','esse','eu','foi','há','isso','isto','já','mais',
    'mas','me','na','nas','no','nos','o','os','ou','para','pela','pelas',
    'pelo','pelos','por','que','se','sem','ser','sua','suas','tem','uma',
    'umas','um','uns','vai','via','à','às','até','após','ante','sob','sobre',
    'em','entre','por','durante','desde','até','como','quando','onde',
}


def _tokenize(text):
    """Tokeniza texto em palavras minúsculas sem stopwords."""
    if not text:
        return []
    tokens = re.findall(r'[a-záàâãéêíóôõúüçA-ZÁÀÂÃÉÊÍÓÔÕÚÜÇ]+', text.lower())
    return [t for t in tokens if len(t) > 2 and t not in _STOPWORDS]


def _ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS nias_market_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            products TEXT,
            regions TEXT,
            price_impact_pct REAL,
            keywords TEXT,
            outcome TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()


_SEED_EVENTS = [
    {
        "event_date": "2018-05-21",
        "event_type": "logistica",
        "title": "Greve dos caminhoneiros",
        "description": "11 dias de bloqueio nacional de rodovias afetando distribuição de alimentos",
        "products": json.dumps(["soja", "milho", "tomate"]),
        "regions": json.dumps(["Brasil"]),
        "price_impact_pct": -18.0,
        "outcome": "PIB -1.2%, frete subiu 300%, perecíveis perdidos R$15bi"
    },
    {
        "event_date": "2020-03-20",
        "event_type": "macro",
        "title": "COVID-19 lockdown portos",
        "description": "Lockdown reduz exportações e paralisa cadeias logísticas portuárias",
        "products": json.dumps(["soja", "milho"]),
        "regions": json.dumps(["Brasil", "Argentina"]),
        "price_impact_pct": -15.0,
        "outcome": "Exportação -18% por 2 meses"
    },
    {
        "event_date": "2021-10-01",
        "event_type": "macro",
        "title": "Crise fertilizantes Rússia",
        "description": "Bloqueio exportação de ureia e fertilizantes nitrogenados pela Rússia",
        "products": json.dumps(["soja", "milho", "algodao"]),
        "regions": json.dumps(["Brasil"]),
        "price_impact_pct": -5.0,
        "outcome": "Preço ureia +180%"
    },
    {
        "event_date": "2022-02-24",
        "event_type": "macro",
        "title": "Guerra Ucrânia grãos bloqueados",
        "description": "Conflito militar bloqueia exportação de grãos do Mar Negro",
        "products": json.dumps(["trigo", "milho", "soja"]),
        "regions": json.dumps(["Brasil", "Argentina"]),
        "price_impact_pct": 25.0,
        "outcome": "Trigo +60%, milho +40%"
    },
    {
        "event_date": "2022-11-01",
        "event_type": "logistica",
        "title": "Bloqueios BR pós-eleição",
        "description": "Bloqueios em rodovias federais após resultado eleitoral paralisam transporte",
        "products": json.dumps(["tomate", "frutas", "legumes"]),
        "regions": json.dumps(["Brasil"]),
        "price_impact_pct": -22.0,
        "outcome": "Perdas R$15bi em perecíveis"
    },
]


def _seed_if_empty(conn):
    count = conn.execute("SELECT COUNT(*) FROM nias_market_memory").fetchone()[0]
    if count > 0:
        return
    for ev in _SEED_EVENTS:
        kw_tokens = _tokenize(ev['title'] + ' ' + ev['description'])
        keywords = ' '.join(set(kw_tokens))
        conn.execute(
            "INSERT INTO nias_market_memory "
            "(event_date,event_type,title,description,products,regions,price_impact_pct,keywords,outcome) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                ev['event_date'], ev['event_type'], ev['title'], ev['description'],
                ev['products'], ev['regions'], ev['price_impact_pct'],
                keywords, ev['outcome']
            )
        )
    conn.commit()


def _similarity_score(query_tokens, row):
    """Score TF-IDF simplificado: fração de tokens da query encontrados no documento."""
    if not query_tokens:
        return 0.0
    doc_text = ' '.join(filter(None, [
        row.get('title', ''),
        row.get('description', ''),
        row.get('keywords', ''),
        row.get('outcome', '')
    ])).lower()
    matches = sum(1 for t in query_tokens if t in doc_text)
    return round(matches / len(query_tokens), 4)


def _search_memory(query):
    conn = get_conn()
    _ensure_table(conn)
    _seed_if_empty(conn)

    tokens = _tokenize(query)
    if not tokens:
        # Sem tokens válidos, retorna os 5 mais recentes
        rows = conn.execute(
            "SELECT * FROM nias_market_memory ORDER BY event_date DESC LIMIT 5"
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d['similarity_score'] = 0.0
            d['products'] = _safe_json(d.get('products'))
            d['regions'] = _safe_json(d.get('regions'))
            results.append(d)
        return results

    # Busca LIKE para cada token
    conditions = []
    params = []
    for t in tokens:
        conditions.append(
            "(LOWER(keywords) LIKE ? OR LOWER(title) LIKE ? OR LOWER(description) LIKE ?)"
        )
        like = f'%{t}%'
        params += [like, like, like]

    where = ' OR '.join(conditions)
    sql = f"SELECT * FROM nias_market_memory WHERE {where} ORDER BY event_date DESC LIMIT 20"
    rows = conn.execute(sql, params).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        d['similarity_score'] = _similarity_score(tokens, d)
        d['products'] = _safe_json(d.get('products'))
        d['regions'] = _safe_json(d.get('regions'))
        results.append(d)

    # Ordena por score desc e retorna top 5
    results.sort(key=lambda x: x['similarity_score'], reverse=True)
    return results[:5]


def _safe_json(val):
    if not val:
        return []
    try:
        return json.loads(val)
    except Exception:
        return [val]


def _store_memory(body_bytes):
    data = json.loads(body_bytes)
    conn = get_conn()
    _ensure_table(conn)

    required = ['event_type', 'title', 'description']
    for f in required:
        if not data.get(f):
            raise ValueError(f"Campo obrigatório ausente: {f}")

    event_date = data.get('event_date') or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    event_type = data['event_type']
    title = data['title']
    description = data['description']
    products = json.dumps(data['products']) if isinstance(data.get('products'), list) else data.get('products', '[]')
    regions = json.dumps(data['regions']) if isinstance(data.get('regions'), list) else data.get('regions', '[]')
    price_impact_pct = data.get('price_impact_pct')
    outcome = data.get('outcome', '')

    kw_tokens = _tokenize(title + ' ' + description + ' ' + outcome)
    keywords = ' '.join(set(kw_tokens))

    cur = conn.execute(
        "INSERT INTO nias_market_memory "
        "(event_date,event_type,title,description,products,regions,price_impact_pct,keywords,outcome) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (event_date, event_type, title, description, products, regions, price_impact_pct, keywords, outcome)
    )
    conn.commit()
    return {'id': cur.lastrowid, 'stored': True, 'keywords_extracted': kw_tokens[:20]}


def _get_query_param(path, param='q'):
    if '?' not in path:
        return ''
    qs = path.split('?', 1)[1]
    params = parse_qs(qs)
    vals = params.get(param, [''])
    return vals[0] if vals else ''


def handle_memory(handler, path):
    """GET /api/nias/memory?q=... — busca na memória de mercado."""
    try:
        query = _get_query_param(path, 'q')
        results = _search_memory(query)
        payload = {
            'query': query,
            'results': results,
            'total': len(results),
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        out = json.dumps(payload, ensure_ascii=False).encode()
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(out)
    except Exception as e:
        err = json.dumps({'error': str(e)}).encode()
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)


def handle_memory_store(handler, path):
    """POST /api/nias/memory/store — armazena novo evento."""
    try:
        length = int(handler.headers.get('Content-Length', 0))
        body = handler.rfile.read(length) if length > 0 else b'{}'
        result = _store_memory(body)
        out = json.dumps(result).encode()
        handler.send_response(201)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(out)
    except Exception as e:
        err = json.dumps({'error': str(e)}).encode()
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)
