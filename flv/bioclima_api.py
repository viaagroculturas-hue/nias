"""NIAS — Módulo Bioclimático ENSO (bioclima_api.py)
Endpoint: GET /api/clima/bioclima?product=soja&months=3
"""
import json
import urllib.request

ENSO_IMPACTS = {
    'soja': {
        'El Niño Forte':    {'BR_south': +12, 'BR_center': -5,  'ARG': +8,  'duration_weeks': 16},
        'El Niño Moderado': {'BR_south': +6,  'BR_center': -2,  'ARG': +4,  'duration_weeks': 12},
        'Neutro':           {'BR_south': 0,   'BR_center': 0,   'ARG': 0,   'duration_weeks': 0},
        'La Niña Moderada': {'BR_south': -8,  'BR_center': +5,  'ARG': -10, 'duration_weeks': 14},
        'La Niña Forte':    {'BR_south': -15, 'BR_center': +8,  'ARG': -18, 'duration_weeks': 18},
    },
    'milho': {
        'El Niño Forte':    {'BR_south': +10, 'BR_center': -3,  'ARG': +6},
        'El Niño Moderado': {'BR_south': +5,  'BR_center': -1,  'ARG': +3},
        'Neutro':           {'BR_south': 0,   'BR_center': 0,   'ARG': 0},
        'La Niña Moderada': {'BR_south': -10, 'BR_center': +4,  'ARG': -12},
        'La Niña Forte':    {'BR_south': -18, 'BR_center': +7,  'ARG': -20},
    },
    'tomate': {
        'El Niño Forte':    {'BR_SE': -15, 'BR_NE': +5,  'notes': 'Chuvas excessivas SE'},
        'El Niño Moderado': {'BR_SE': -8,  'BR_NE': +3},
        'Neutro':           {'BR_SE': 0,   'BR_NE': 0},
        'La Niña Moderada': {'BR_SE': +5,  'BR_NE': -10, 'notes': 'Seca NE'},
        'La Niña Forte':    {'BR_SE': +8,  'BR_NE': -18},
    },
    'trigo': {
        'El Niño Forte':    {'BR_south': +15, 'ARG': +10, 'notes': 'Excesso chuva no RS/PR'},
        'El Niño Moderado': {'BR_south': +8,  'ARG': +5},
        'Neutro':           {'BR_south': 0,   'ARG': 0},
        'La Niña Moderada': {'BR_south': -12, 'ARG': -15},
        'La Niña Forte':    {'BR_south': -20, 'ARG': -22, 'notes': 'Seca severa Cone Sul'},
    },
    'cafe': {
        'El Niño Forte':    {'MG': -10, 'ES': -8,  'notes': 'Geadas tardias e veranicos MG'},
        'El Niño Moderado': {'MG': -5,  'ES': -3},
        'Neutro':           {'MG': 0,   'ES': 0},
        'La Niña Moderada': {'MG': +5,  'ES': +4,  'notes': 'Boa floração'},
        'La Niña Forte':    {'MG': +8,  'ES': +6},
    },
    'cana': {
        'El Niño Forte':    {'SP': +5,  'NE': -20, 'notes': 'Seca severa NE'},
        'El Niño Moderado': {'SP': +3,  'NE': -10},
        'Neutro':           {'SP': 0,   'NE': 0},
        'La Niña Moderada': {'SP': -5,  'NE': +8},
        'La Niña Forte':    {'SP': -10, 'NE': +15, 'notes': 'Chuvas NE acima da média'},
    },
    'arroz': {
        'El Niño Forte':    {'RS': +12, 'MT': -8,  'notes': 'Chuvas RS favoráveis'},
        'El Niño Moderado': {'RS': +6,  'MT': -4},
        'Neutro':           {'RS': 0,   'MT': 0},
        'La Niña Moderada': {'RS': -10, 'MT': +5},
        'La Niña Forte':    {'RS': -18, 'MT': +8,  'notes': 'Seca RS crítica'},
    },
}

HISTORICAL_NOTES = {
    'El Niño Forte':    'El Niño Forte associado a chuvas acima da média no Sul e seca no Norte/Nordeste (2015-16, 1997-98).',
    'El Niño Moderado': 'El Niño Moderado traz variações regionais menores, com tendência a chuvas no Sul.',
    'Neutro':           'Fase neutra do ENSO: padrões climáticos dentro da normalidade histórica.',
    'La Niña Moderada': 'La Niña Moderada associada a seca no Sul e chuvas acima da média no Norte/NE (2010-11).',
    'La Niña Forte':    'La Niña Forte causa seca severa no Sul e Sudeste, impactando safras de soja e milho.',
}

RECOMMENDATIONS = {
    'El Niño Forte':    'Monitorar excesso hídrico; avaliar seguro agrícola para culturas sensíveis a chuva.',
    'El Niño Moderado': 'Atenção ao calendário de plantio; janela favorável no Sul para soja/milho.',
    'Neutro':           'Condições normais; seguir calendário padrão de plantio e manejo.',
    'La Niña Moderada': 'Planejar irrigação suplementar no Sul; oportunidade para cultura no Norte.',
    'La Niña Forte':    'Alta probabilidade de frustração de safra no Sul; diversificar e antecipar contratos.',
}


def _parse_qs(path):
    params = {}
    if '?' in path:
        qs = path.split('?', 1)[1]
        for part in qs.split('&'):
            if '=' in part:
                k, v = part.split('=', 1)
                params[k] = v.replace('+', ' ').replace('%20', ' ')
    return params


def _fetch_oni():
    """Busca índice ONI atual via NOAA. Retorna (oni_value, source)."""
    url = 'https://origin.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/detrend.nino34.ascii.txt'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'NIAS/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            text = resp.read().decode('utf-8', errors='ignore')
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        # Skip header lines (start with letters)
        data_lines = [l for l in lines if l and l[0].isdigit()]
        if data_lines:
            last = data_lines[-1].split()
            # Format: YR MON TOTAL CLIM ANOM
            oni = float(last[-1])  # last column = anomaly
            return oni, 'noaa'
    except Exception:
        pass
    return 0.5, 'fallback'


def _classify_oni(oni):
    if oni > 1.5:
        return 'El Niño Forte'
    elif oni > 0.5:
        return 'El Niño Moderado'
    elif oni > -0.5:
        return 'Neutro'
    elif oni > -1.5:
        return 'La Niña Moderada'
    else:
        return 'La Niña Forte'


def handle_bioclima(handler, path):
    try:
        params = _parse_qs(path)
        product = params.get('product', 'soja').lower()
        try:
            months = max(1, min(24, int(params.get('months', 3))))
        except ValueError:
            months = 3

        oni_value, oni_source = _fetch_oni()
        enso_phase = _classify_oni(oni_value)

        # Regional impacts for product
        product_impacts = ENSO_IMPACTS.get(product, {})
        phase_impacts = product_impacts.get(enso_phase, {})

        # Compute average numeric impact (exclude non-numeric keys)
        numeric_values = [v for k, v in phase_impacts.items()
                          if isinstance(v, (int, float)) and k not in ('duration_weeks',)]
        avg_impact = sum(numeric_values) / len(numeric_values) if numeric_values else 0.0

        # Confidence
        if oni_source == 'noaa' and product in ENSO_IMPACTS:
            confidence = 'alta'
        elif oni_source == 'noaa' or product in ENSO_IMPACTS:
            confidence = 'media'
        else:
            confidence = 'baixa'

        # Regional impacts clean (only numeric)
        regional_impacts = {k: v for k, v in phase_impacts.items()
                            if isinstance(v, (int, float)) and k not in ('duration_weeks',)}

        result = {
            'product': product,
            'oni_value': round(oni_value, 2),
            'enso_phase': enso_phase,
            'price_impact_pct': round(avg_impact, 2),
            'regional_impacts': regional_impacts,
            'outlook_months': months,
            'confidence': confidence,
            'historical_note': HISTORICAL_NOTES.get(enso_phase, ''),
            'recommendation': RECOMMENDATIONS.get(enso_phase, ''),
            'oni_source': oni_source,
            'product_covered': product in ENSO_IMPACTS,
        }

        data = json.dumps(result).encode()
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
