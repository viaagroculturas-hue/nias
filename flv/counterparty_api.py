"""NIAS — Módulo Score de Risco de Contraparte (counterparty_api.py)
Endpoint: GET /api/risk/produtor?id=123
         GET /api/risk/produtor?name=fazenda+xpto&state=MT
"""
import json
from flv.db import get_conn

HIGH_VALUE_CULTURES = {'soja', 'cafe', 'uva', 'cacau', 'erva-mate', 'algodao'}
LOW_RISK_STATES = {'PR', 'RS', 'GO', 'SC', 'MT'}  # boas condições agroclimáticas

def _parse_qs(path):
    params = {}
    if '?' in path:
        qs = path.split('?', 1)[1]
        for part in qs.split('&'):
            if '=' in part:
                k, v = part.split('=', 1)
                params[k] = v.replace('+', ' ').replace('%20', ' ')
    return params


def _fetch_produtor(produtor_id, name, state):
    conn = get_conn()
    try:
        if produtor_id:
            row = conn.execute(
                'SELECT * FROM produtores WHERE id = ?', (produtor_id,)
            ).fetchone()
        elif name:
            name_pattern = f'%{name}%'
            if state:
                row = conn.execute(
                    'SELECT * FROM produtores WHERE name LIKE ? AND state_uf = ?',
                    (name_pattern, state.upper())
                ).fetchone()
            else:
                row = conn.execute(
                    'SELECT * FROM produtores WHERE name LIKE ?', (name_pattern,)
                ).fetchone()
        else:
            row = None
        return dict(row) if row else None
    except Exception:
        return None


def _fetch_judicial_count(entity_name):
    if not entity_name:
        return 0
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM flv_judicial WHERE entity_name LIKE ? AND status = 'ativo'",
            (f'%{entity_name}%',)
        ).fetchone()
        return int(row['cnt']) if row else 0
    except Exception:
        return 0


def _classify_score(score):
    if score >= 800:
        return 'PREMIUM'
    elif score >= 600:
        return 'REGULAR'
    elif score >= 400:
        return 'MONITORAR'
    elif score >= 200:
        return 'CAUTELA'
    else:
        return 'CRÍTICO'


def _build_score(produtor):
    breakdown = {'area': 0, 'cultura': 0, 'zona': 0, 'experiencia': 0, 'judicial': 0}
    risk_factors = []
    positive_factors = []
    base = 500

    if produtor is None:
        return base, breakdown, risk_factors, positive_factors, 'minimo'

    # Area
    area = None
    for key in ('area_ha', 'area', 'hectares'):
        if key in produtor and produtor[key] is not None:
            try:
                area = float(produtor[key])
                break
            except (ValueError, TypeError):
                pass

    if area is not None:
        if area > 5000:
            breakdown['area'] = 120
            positive_factors.append(f'Grande produtor: {area:.0f} ha')
        elif area > 1000:
            breakdown['area'] = 80
            positive_factors.append(f'Médio-grande produtor: {area:.0f} ha')
        elif area < 50:
            risk_factors.append(f'Área pequena ({area:.0f} ha): menor capacidade produtiva')

    # Cultura
    culture = (produtor.get('main_culture') or '').lower()
    if any(c in culture for c in HIGH_VALUE_CULTURES):
        breakdown['cultura'] = 50
        positive_factors.append(f'Cultura de alto valor: {culture}')

    # Zona climática
    state = (produtor.get('state_uf') or '').upper()
    if state in LOW_RISK_STATES:
        breakdown['zona'] = 60
        positive_factors.append(f'Zona climática favorável: {state}')
    elif state in {'PI', 'MA', 'CE', 'RN', 'PB', 'AL', 'SE'}:
        risk_factors.append(f'Zona climática com risco de seca: {state}')

    # Experiência (anos em operação)
    founded = produtor.get('founded_year')
    if founded:
        try:
            import datetime
            years = datetime.datetime.now().year - int(founded)
            if years > 10:
                breakdown['experiencia'] = 80
                positive_factors.append(f'Mais de {years} anos em operação')
            elif years < 3:
                risk_factors.append(f'Empresa recente ({years} anos)')
        except (ValueError, TypeError):
            pass

    # Judicial
    entity_name = produtor.get('name', '')
    judicial_count = _fetch_judicial_count(entity_name)
    if judicial_count > 0:
        penalty = min(200 * judicial_count, 400)
        breakdown['judicial'] = -penalty
        risk_factors.append(f'{judicial_count} processo(s) judicial(is) ativo(s)')
    else:
        positive_factors.append('Sem processos judiciais ativos')

    # Data completeness
    fields_present = sum(1 for f in ('area_ha', 'main_culture', 'state_uf', 'founded_year', 'cnpj', 'cpf')
                         if produtor.get(f))
    if fields_present >= 4:
        completeness = 'completo'
    elif fields_present >= 2:
        completeness = 'parcial'
    else:
        completeness = 'minimo'

    total = base + sum(breakdown.values())
    total = max(0, min(1000, total))
    return total, breakdown, risk_factors, positive_factors, completeness


def _recommendation(classification):
    msgs = {
        'PREMIUM':   'Contraparte confiável. Operações de grande porte recomendadas sem restrições.',
        'REGULAR':   'Contraparte adequada. Acompanhamento periódico recomendado.',
        'MONITORAR': 'Contraparte com pontos de atenção. Monitorar regularmente e exigir garantias.',
        'CAUTELA':   'Alto risco identificado. Exigir garantias reais e limitar exposição.',
        'CRÍTICO':   'Não recomendado operar. Risco muito elevado de inadimplência ou falência.',
    }
    return msgs.get(classification, '')


def handle_produtor(handler, path):
    try:
        params = _parse_qs(path)
        produtor_id = params.get('id', '').strip() or None
        name = params.get('name', '').strip() or None
        state = params.get('state', '').strip() or None

        produtor = _fetch_produtor(produtor_id, name, state)

        score, breakdown, risk_factors, positive_factors, completeness = _build_score(produtor)
        classification = _classify_score(score)

        result = {
            'produtor_id': produtor.get('id') if produtor else produtor_id,
            'name': produtor.get('name') if produtor else name,
            'state': produtor.get('state_uf') if produtor else state,
            'found_in_db': produtor is not None,
            'score': score,
            'classification': classification,
            'score_breakdown': breakdown,
            'risk_factors': risk_factors,
            'positive_factors': positive_factors,
            'recommendation': _recommendation(classification),
            'data_completeness': completeness,
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
