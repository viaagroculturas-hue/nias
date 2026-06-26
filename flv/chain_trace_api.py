"""NIAS — Módulo de Rastreabilidade Farm-to-Fork (chain_trace_api.py)
Endpoints:
  GET  /api/chain/trace?lot_id=xxx
  POST /api/chain/register  (body JSON)
  GET  /api/chain/lots?product=tomate&days=7
"""
import json
import re
from datetime import datetime, timedelta
from flv.db import get_conn

CREATE_LOTS = """
CREATE TABLE IF NOT EXISTS chain_lots (
    lot_id TEXT PRIMARY KEY,
    product TEXT NOT NULL,
    producer_name TEXT,
    origin_city TEXT,
    origin_state TEXT,
    quantity_kg REAL,
    harvest_date TEXT,
    created_at TEXT DEFAULT (datetime('now'))
)
"""

CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS chain_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lot_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    actor TEXT NOT NULL,
    quantity_kg REAL,
    location TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    notes TEXT,
    FOREIGN KEY (lot_id) REFERENCES chain_lots(lot_id)
)
"""

VALID_STAGES = {'colheita', 'transporte', 'ceasa', 'distribuidor', 'varejo', 'consumidor'}


def _ensure_tables():
    conn = get_conn()
    conn.execute(CREATE_LOTS)
    conn.execute(CREATE_EVENTS)
    conn.commit()


def _parse_qs(path):
    params = {}
    if '?' in path:
        qs = path.split('?', 1)[1]
        for part in qs.split('&'):
            if '=' in part:
                k, v = part.split('=', 1)
                params[k] = v.replace('+', ' ').replace('%20', ' ')
    return params


def _read_body(handler):
    length = int(handler.headers.get('Content-Length', 0))
    if length > 0:
        raw = handler.rfile.read(length)
        return json.loads(raw.decode('utf-8'))
    return {}


def _get_lot(conn, lot_id):
    try:
        row = conn.execute('SELECT * FROM chain_lots WHERE lot_id = ?', (lot_id,)).fetchone()
        return dict(row) if row else None
    except Exception:
        return None


def _get_events(conn, lot_id):
    try:
        rows = conn.execute(
            'SELECT * FROM chain_events WHERE lot_id = ? ORDER BY timestamp ASC',
            (lot_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ─── GET /api/chain/trace ─────────────────────────────────────────────────────

def handle_trace(handler, path):
    try:
        _ensure_tables()
        params = _parse_qs(path)
        lot_id = params.get('lot_id', '').strip()
        if not lot_id:
            raise ValueError('lot_id é obrigatório')

        conn = get_conn()
        lot = _get_lot(conn, lot_id)
        if not lot:
            data = json.dumps({'found': False, 'lot_id': lot_id}).encode()
            handler.send_response(404)
            handler.send_header('Content-Type', 'application/json')
            handler.send_header('Access-Control-Allow-Origin', '*')
            handler.end_headers()
            handler.wfile.write(data)
            return

        events = _get_events(conn, lot_id)

        # Calcular tempo total e perda
        tempo_total_dias = None
        perda_pct = None
        if events:
            try:
                t_first = datetime.fromisoformat(events[0]['timestamp'])
                t_last = datetime.fromisoformat(events[-1]['timestamp'])
                tempo_total_dias = round((t_last - t_first).total_seconds() / 86400, 2)
            except Exception:
                pass

            qty_inicial = lot.get('quantity_kg')
            qty_final = None
            for ev in reversed(events):
                if ev.get('quantity_kg') is not None:
                    qty_final = ev['quantity_kg']
                    break
            if qty_inicial and qty_final is not None and qty_inicial > 0:
                perda_pct = round((qty_inicial - qty_final) / qty_inicial * 100, 2)

        timeline = []
        for ev in events:
            timeline.append({
                'stage': ev.get('stage'),
                'actor': ev.get('actor'),
                'quantity_kg': ev.get('quantity_kg'),
                'location': ev.get('location'),
                'timestamp': ev.get('timestamp'),
                'notes': ev.get('notes'),
            })

        result = {
            'lot_id': lot_id,
            'product': lot.get('product'),
            'producer_name': lot.get('producer_name'),
            'origin_city': lot.get('origin_city'),
            'origin_state': lot.get('origin_state'),
            'quantity_kg_original': lot.get('quantity_kg'),
            'harvest_date': lot.get('harvest_date'),
            'created_at': lot.get('created_at'),
            'timeline': timeline,
            'stages_count': len(events),
            'tempo_total_dias': tempo_total_dias,
            'perda_pct': perda_pct,
            'current_stage': events[-1]['stage'] if events else None,
        }

        data = json.dumps(result, ensure_ascii=False).encode()
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(data)

    except Exception as e:
        err = json.dumps({'error': str(e)}).encode()
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)


# ─── POST /api/chain/register ─────────────────────────────────────────────────

def handle_register(handler, path):
    try:
        _ensure_tables()
        body = _read_body(handler)

        lot_id = (body.get('lot_id') or '').strip()
        stage = (body.get('stage') or '').strip().lower()
        actor = (body.get('actor') or '').strip()

        if not lot_id:
            raise ValueError('lot_id é obrigatório')
        if not stage:
            raise ValueError('stage é obrigatório')
        if not actor:
            raise ValueError('actor é obrigatório')

        quantity_kg = body.get('quantity_kg')
        if quantity_kg is not None:
            quantity_kg = float(quantity_kg)

        origin = body.get('origin', '')
        destination = body.get('destination', '')
        notes = body.get('notes', '')
        location = destination or origin or None

        conn = get_conn()
        lot = _get_lot(conn, lot_id)

        # Criar lot na primeira vez (stage = colheita)
        if lot is None:
            product = body.get('product', 'desconhecido')
            producer_name = body.get('producer_name') or actor
            origin_city = body.get('origin_city') or origin or None
            origin_state = body.get('origin_state') or None
            harvest_date = body.get('harvest_date') or datetime.now().strftime('%Y-%m-%d')
            conn.execute(
                """INSERT OR IGNORE INTO chain_lots
                   (lot_id, product, producer_name, origin_city, origin_state, quantity_kg, harvest_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (lot_id, product, producer_name, origin_city, origin_state, quantity_kg, harvest_date)
            )

        # Inserir evento
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """INSERT INTO chain_events (lot_id, stage, actor, quantity_kg, location, timestamp, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (lot_id, stage, actor, quantity_kg, location, now_str, notes or None)
        )
        conn.commit()

        # Contar events
        count_row = conn.execute(
            'SELECT COUNT(*) AS cnt FROM chain_events WHERE lot_id = ?', (lot_id,)
        ).fetchone()
        events_count = count_row['cnt'] if count_row else 0

        result = {
            'success': True,
            'lot_id': lot_id,
            'stage_recorded': stage,
            'actor': actor,
            'quantity_kg': quantity_kg,
            'timestamp': now_str,
            'events_count': events_count,
            'lot_created': lot is None,
        }

        data = json.dumps(result, ensure_ascii=False).encode()
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(data)

    except Exception as e:
        err = json.dumps({'error': str(e)}).encode()
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)


# ─── GET /api/chain/lots ──────────────────────────────────────────────────────

def handle_lots(handler, path):
    try:
        _ensure_tables()
        params = _parse_qs(path)
        product = params.get('product', '').strip()
        try:
            days = max(1, min(365, int(params.get('days', 7))))
        except ValueError:
            days = 7

        since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        conn = get_conn()

        if product:
            rows = conn.execute(
                """SELECT l.*,
                   (SELECT stage FROM chain_events e WHERE e.lot_id = l.lot_id
                    ORDER BY e.timestamp DESC LIMIT 1) AS current_stage,
                   (SELECT COUNT(*) FROM chain_events e WHERE e.lot_id = l.lot_id) AS events_count
                   FROM chain_lots l
                   WHERE l.product = ? AND l.created_at >= ?
                   ORDER BY l.created_at DESC""",
                (product, since)
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT l.*,
                   (SELECT stage FROM chain_events e WHERE e.lot_id = l.lot_id
                    ORDER BY e.timestamp DESC LIMIT 1) AS current_stage,
                   (SELECT COUNT(*) FROM chain_events e WHERE e.lot_id = l.lot_id) AS events_count
                   FROM chain_lots l
                   WHERE l.created_at >= ?
                   ORDER BY l.created_at DESC""",
                (since,)
            ).fetchall()

        lots = [dict(r) for r in rows]

        result = {
            'product': product or 'todos',
            'days': days,
            'since': since,
            'total': len(lots),
            'lots': lots,
        }

        data = json.dumps(result, ensure_ascii=False).encode()
        handler.send_response(200)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(data)

    except Exception as e:
        err = json.dumps({'error': str(e)}).encode()
        handler.send_response(500)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)


# ─── Router principal ─────────────────────────────────────────────────────────

def handle_chain(handler, path):
    """Dispatcher para todos os endpoints /api/chain/*"""
    if '/trace' in path:
        handle_trace(handler, path)
    elif '/register' in path:
        handle_register(handler, path)
    elif '/lots' in path:
        handle_lots(handler, path)
    else:
        err = json.dumps({'error': 'Endpoint não encontrado. Use /trace, /register ou /lots'}).encode()
        handler.send_response(404)
        handler.send_header('Content-Type', 'application/json')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.end_headers()
        handler.wfile.write(err)
