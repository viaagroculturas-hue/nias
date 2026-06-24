"""
FLV Pipeline Scheduler — Trava anti-duplicação, registro de status e execução programada.
"""
import json, os, time, threading, traceback
from datetime import datetime

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_STATUS_PATH = os.path.join(_ROOT, 'data', 'pipeline_status.json')

_lock = threading.Lock()


def _read_status() -> dict:
    """Lê status persistido do pipeline."""
    default = {
        'running': False,
        'started_at': None,
        'last_success': None,
        'last_error': None,
        'duration_seconds': None,
        'runs_total': 0,
        'runs_success': 0,
        'runs_failed': 0,
    }
    try:
        if os.path.exists(_STATUS_PATH):
            with open(_STATUS_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Merge defaults
            for k, v in default.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    return default


def _write_status(status: dict):
    """Persiste status do pipeline."""
    try:
        os.makedirs(os.path.dirname(_STATUS_PATH), exist_ok=True)
        with open(_STATUS_PATH, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def is_pipeline_running() -> bool:
    """Verifica se o pipeline está rodando agora."""
    status = _read_status()
    if not status.get('running'):
        return False
    # Safety: se started_at > 10min atrás, considerar travado
    started = status.get('started_at')
    if started:
        try:
            dt = datetime.fromisoformat(started)
            if (datetime.now() - dt).total_seconds() > 600:
                # Reset stale lock
                status['running'] = False
                _write_status(status)
                return False
        except Exception:
            pass
    return True


def get_pipeline_status() -> dict:
    """Retorna status completo do pipeline para endpoint."""
    status = _read_status()
    # Adicionar freshness do banco
    freshness = _get_freshness_summary()
    status['freshness'] = freshness
    status['next_run_hint'] = '6h após última execução'
    return status


def _get_freshness_summary() -> dict:
    """Resumo de freshness das tabelas principais."""
    import sqlite3
    db_path = os.environ.get('NIAS_DB_PATH') or os.path.join(_ROOT, 'data', 'nia_flv.db')
    result = {}
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        queries = {
            'prices': "SELECT MAX(price_date) as d FROM flv_ceasa_prices",
            'climate': "SELECT MAX(obs_date) as d FROM flv_climate",
            'news': "SELECT MAX(obs_date) as d FROM flv_news_risk_daily",
            'macro': "SELECT MAX(obs_date) as d FROM flv_macro_indicators",
        }
        for key, sql in queries.items():
            try:
                row = conn.execute(sql).fetchone()
                result[key] = row['d'] if row else None
            except Exception:
                result[key] = None
        conn.close()
    except Exception:
        pass
    return result


def run_pipeline_once() -> dict:
    """
    Executa o pipeline uma vez com trava anti-duplicação.
    Retorna dict com status da execução.
    """
    if is_pipeline_running():
        return {
            'status': 'skipped',
            'reason': 'Pipeline já está em execução',
            'running_since': _read_status().get('started_at')
        }

    with _lock:
        status = _read_status()
        status['running'] = True
        status['started_at'] = datetime.now().isoformat()
        _write_status(status)

    t0 = time.time()
    error_msg = None
    try:
        from flv.pipeline import run_pipeline
        run_pipeline()
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        traceback.print_exc()

    elapsed = time.time() - t0

    with _lock:
        status = _read_status()
        status['running'] = False
        status['duration_seconds'] = round(elapsed, 1)
        status['runs_total'] = (status.get('runs_total') or 0) + 1
        if error_msg:
            status['last_error'] = error_msg
            status['last_error_at'] = datetime.now().isoformat()
            status['runs_failed'] = (status.get('runs_failed') or 0) + 1
        else:
            status['last_success'] = datetime.now().isoformat()
            status['last_error'] = None
            status['runs_success'] = (status.get('runs_success') or 0) + 1
        _write_status(status)

    return {
        'status': 'error' if error_msg else 'ok',
        'duration_seconds': round(elapsed, 1),
        'error': error_msg,
        'timestamp': datetime.now().isoformat()
    }


# ─── CLI: python -m flv.scheduler ────────────────────────────────────
if __name__ == '__main__':
    import sys
    if '--loop' in sys.argv:
        hours = 6
        for i, arg in enumerate(sys.argv):
            if arg == '--hours' and i + 1 < len(sys.argv):
                hours = int(sys.argv[i + 1])
        print(f'[Scheduler] Modo loop: executando a cada {hours}h')
        while True:
            run_pipeline_once()
            time.sleep(hours * 3600)
    else:
        print('[Scheduler] Execução única')
        result = run_pipeline_once()
        print(json.dumps(result, ensure_ascii=False, indent=2))
