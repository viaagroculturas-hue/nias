"""
FLV CLIMAPI Client — Acesso à AgroAPI da Embrapa (ClimAPI) com fallback para Open-Meteo.
========================================================================================
Tenta autenticar via OAuth2 na AgroAPI. Se falhar, usa Open-Meteo como substituto.
"""
import os, time, json
from datetime import datetime
from typing import Optional

# Credenciais via variáveis de ambiente (NUNCA hardcoded)
AGROAPI_CLIENT_ID = os.environ.get('AGROAPI_CLIENT_ID', '')
AGROAPI_CLIENT_SECRET = os.environ.get('AGROAPI_CLIENT_SECRET', '')
AGROAPI_TOKEN_URL = os.environ.get('AGROAPI_TOKEN_URL', 'https://api.cnptia.embrapa.br/token')
CLIMAPI_BASE_URL = os.environ.get('CLIMAPI_BASE_URL', 'https://api.cnptia.embrapa.br/climapi/v1')

_token_cache = {
    'access_token': None,
    'expires_at': 0,
}


def _get_token() -> Optional[str]:
    """Obtém token OAuth2 da AgroAPI. Retorna None se credenciais ausentes ou inválidas."""
    if not AGROAPI_CLIENT_ID or not AGROAPI_CLIENT_SECRET:
        return None

    # Cache válido?
    if _token_cache['access_token'] and time.time() < _token_cache['expires_at']:
        return _token_cache['access_token']

    try:
        import requests
        import base64
        # Basic auth: client_id:client_secret em base64
        credentials = base64.b64encode(f"{AGROAPI_CLIENT_ID}:{AGROAPI_CLIENT_SECRET}".encode()).decode()
        resp = requests.post(
            AGROAPI_TOKEN_URL,
            headers={'Authorization': f'Basic {credentials}'},
            data={'grant_type': 'client_credentials'},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            _token_cache['access_token'] = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            _token_cache['expires_at'] = time.time() + expires_in - 60  # Margem de segurança
            return _token_cache['access_token']
        else:
            _token_cache['access_token'] = None
            return None
    except Exception:
        return None


def test_climapi_connection() -> dict:
    """Testa conexão com a AgroAPI/ClimAPI. Retorna diagnóstico completo."""
    result = {
        'credentials_present': bool(AGROAPI_CLIENT_ID and AGROAPI_CLIENT_SECRET),
        'client_id_set': bool(AGROAPI_CLIENT_ID),
        'credentials_configured': bool(AGROAPI_CLIENT_SECRET),
        'token_url': AGROAPI_TOKEN_URL,
        'base_url': CLIMAPI_BASE_URL,
    }

    if not result['credentials_present']:
        result['status'] = 'fallback'
        result['reason'] = 'Credenciais AgroAPI (client_id/credentials) não configuradas nas variáveis de ambiente'
        result['token_valid'] = False
        result['replacement'] = 'Open-Meteo'
        return result

    token = _get_token()
    if not token:
        result['status'] = 'error'
        result['reason'] = 'Falha na autenticação OAuth2. Token não obtido (credenciais expiradas ou inválidas).'
        result['token_valid'] = False
        result['replacement'] = 'Open-Meteo'
        return result

    # Tentar chamada simples
    try:
        import requests
        resp = requests.get(
            f"{CLIMAPI_BASE_URL}/forecasts",
            headers={'Authorization': f'Bearer {token}'},
            params={'lat': -23.5, 'lon': -46.6},
            timeout=10
        )
        if resp.status_code == 200:
            result['status'] = 'real'
            result['token_valid'] = True
            result['last_success'] = datetime.now().isoformat()
            result['reason'] = None
        elif resp.status_code == 401:
            result['status'] = 'error'
            result['token_valid'] = False
            result['reason'] = f'Token rejeitado (HTTP 401). Credenciais expiradas.'
            result['replacement'] = 'Open-Meteo'
        elif resp.status_code == 429:
            result['status'] = 'error'
            result['token_valid'] = True
            result['reason'] = f'Cota excedida (HTTP 429). Rate limit atingido.'
            result['replacement'] = 'Open-Meteo'
        else:
            result['status'] = 'error'
            result['token_valid'] = True
            result['reason'] = f'Resposta inesperada HTTP {resp.status_code}'
            result['replacement'] = 'Open-Meteo'
    except Exception as e:
        result['status'] = 'error'
        result['token_valid'] = False
        result['reason'] = f'Erro de conexão: {type(e).__name__}: {e}'
        result['replacement'] = 'Open-Meteo'

    return result


def fetch_climapi_forecast(lat: float, lon: float) -> Optional[dict]:
    """Busca previsão climática da AgroAPI. Retorna None se indisponível."""
    token = _get_token()
    if not token:
        return None
    try:
        import requests
        resp = requests.get(
            f"{CLIMAPI_BASE_URL}/forecasts",
            headers={'Authorization': f'Bearer {token}'},
            params={'lat': lat, 'lon': lon},
            timeout=15
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def get_climapi_status() -> dict:
    """Status resumido para /api/sources/status."""
    diag = test_climapi_connection()
    return {
        'status': diag['status'],
        'credentials_present': diag['credentials_present'],
        'token_valid': diag.get('token_valid', False),
        'reason': diag.get('reason'),
        'last_success': diag.get('last_success'),
        'replacement': diag.get('replacement', 'Open-Meteo'),
        'fallback_active': diag['status'] != 'real',
    }
