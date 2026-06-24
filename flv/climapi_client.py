"""
ClimAPI Client — stub para endpoints que dependem de ClimAPI.
ClimAPI requer autenticação paga. O NIA$ usa Open-Meteo como fonte gratuita.
"""


def get_climapi_status():
    """Retorna status do ClimAPI (não disponível — usa Open-Meteo)."""
    return {
        'status': 'unavailable',
        'reason': 'ClimAPI requer autenticacao paga (HTTP 401). NIA$ usa Open-Meteo como alternativa gratuita.',
        'replacement': 'Open-Meteo',
        'fallback_active': True,
        'description': 'ClimAPI CPTEC/INPE (requer credencial)'
    }
