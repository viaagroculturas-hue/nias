"""Envelope padrão de resposta para NIAS API Core."""
import json
from datetime import datetime
from flv.nias_api import API_VERSION, API_NAME


def ok(data: dict, *, mode: str = 'real_data', sources: list = None, confidence: str = 'media') -> dict:
    """Resposta de sucesso padronizada."""
    return {
        'status': 'ok',
        'api': API_NAME,
        'version': API_VERSION,
        'mode': mode,
        'data': data,
        'meta': {
            'sources': sources or [],
            'updated_at': datetime.now().isoformat(),
            'confidence': confidence,
        }
    }


def error(message: str, details: str = None) -> dict:
    """Resposta de erro padronizada."""
    r = {
        'status': 'error',
        'api': API_NAME,
        'version': API_VERSION,
        'message': message,
    }
    if details:
        r['details'] = details
    return r


def partial(data: dict, message: str, *, missing: list = None, sources: list = None) -> dict:
    """Resposta parcial / dados insuficientes."""
    return {
        'status': 'partial',
        'api': API_NAME,
        'version': API_VERSION,
        'mode': 'insufficient_data',
        'message': message,
        'missing': missing or [],
        'data': data,
        'meta': {
            'sources': sources or [],
            'updated_at': datetime.now().isoformat(),
            'confidence': 'baixa',
        }
    }
