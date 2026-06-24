"""
FLV Pipeline Scheduler — Trava anti-duplicação, logs detalhados e histórico de execuções.
"""
import json, os, time, threading, traceback, uuid, platform
from datetime import datetime

from flv.paths import get_pipeline_status_path, get_pipeline_runs_path, get_scheduler_log_path, get_db_path

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
    path = get_pipeline_status_path()
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for k, v in default.items():
                data.setdefault(k, v)
            return data
    except Exception:
        pass
    return default


def _write_status(status: dict):
    """Persiste status do pipeline."""
    path = get_pipeline_status_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(status, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass


def _log(msg: str):
    """Append ao log do scheduler."""
    try:
        path = get_scheduler_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f'[{ts}] {msg}\n')
    except Exception:
        pass


def _append_run(run: dict):
    """Append ao histórico de runs (JSONL)."""
    try:
        path = get_pipeline_runs_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(run, ensure_ascii=False, default=str) + '\n')
    except Exception:
        pass


def _get_freshness_snapshot() -> dict:
    """Snapshot de freshness antes/depois do pipeline."""
    import sqlite3
    db_path = str(get_db_path())
    result = {'prices': None, 'climate': None, 'news': None, 'macro': None}
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        queries = {
            'prices': "SELECT MAX(price_date) as d, COUNT(*) as n FROM flv_ceasa_prices",
            'climate': "SELECT MAX(obs_date) as d, COUNT(*) as n FROM flv_climate",
            'news': "SELECT MAX(obs_date) as d, COUNT(*) as n FROM flv_news_risk_daily",
            'macro': "SELECT MAX(obs_date) as d, COUNT(*) as n FROM flv_macro_indicators",
        }
        for key, sql in queries.items():
            try:
                row = conn.execute(sql).fetchone()
                result[key] = {'max_date': row['d'], 'count': row['n']} if row else None
            except Exception:
                pass
        conn.close()
    except Exception:
        pass
    return result


def is_pipeline_running() -> bool:
    """Verifica se o pipeline está rodando agora."""
    status = _read_status()
    if not status.get('running'):
        return False
    started = status.get('started_at')
    if started:
        try:
            dt = datetime.fromisoformat(started)
            if (datetime.now() - dt).total_seconds() > 600:
                status['running'] = False
                _write_status(status)
                _log('WARN: Lock stale detectado (>10min). Resetado.')
                return False
        except Exception:
            pass
    return True


def get_pipeline_status() -> dict:
    """Retorna status completo do pipeline para endpoint."""
    from flv.paths import get_storage_info
    status = _read_status()
    freshness = _get_freshness_snapshot()
    status['freshness'] = {k: v['max_date'] if v else None for k, v in freshness.items()}
    status['next_run_hint'] = '6h após última execução'
    status['storage'] = get_storage_info()
    return status


def get_pipeline_runs(limit: int = 20) -> list:
    """Retorna últimas N execuções do pipeline."""
    path = get_pipeline_runs_path()
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        runs = []
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                try:
                    runs.append(json.loads(line))
                except Exception:
                    pass
        return list(reversed(runs))  # Mais recente primeiro
    except Exception:
        return []


def get_pipeline_logs(limit: int = 50) -> list:
    """Retorna últimas N linhas do log do scheduler."""
    path = get_scheduler_log_path()
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        return [l.rstrip() for l in lines[-limit:]]
    except Exception:
        return []


def get_pipeline_freshness() -> dict:
    """Retorna freshness detalhada com status."""
    snapshot = _get_freshness_snapshot()
    today = datetime.now().strftime('%Y-%m-%d')
    result = {}
    for key, val in snapshot.items():
        if val and val.get('max_date'):
            max_date = val['max_date']
            try:
                days_old = (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(max_date, '%Y-%m-%d')).days
            except Exception:
                days_old = 999
            if days_old <= 2:
                status = 'fresh'
            elif days_old <= 7:
                status = 'stale'
            else:
                status = 'critical'
            result[key] = {'max_date': max_date, 'count': val.get('count', 0), 'days_old': days_old, 'status': status}
        else:
            result[key] = {'max_date': None, 'count': 0, 'days_old': None, 'status': 'empty'}
    return result


def run_pipeline_once(trigger: str = 'manual') -> dict:
    """
    Executa o pipeline uma vez com trava, logs detalhados e registro no histórico.
    """
    if is_pipeline_running():
        msg = 'SKIP: Pipeline já em execução'
        _log(msg)
        return {
            'status': 'skipped',
            'reason': msg,
            'running_since': _read_status().get('started_at')
        }

    run_id = datetime.now().strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:4]
    _log(f'START run_id={run_id} trigger={trigger} pid={os.getpid()} host={platform.node()}')

    # Snapshot ANTES
    before = _get_freshness_snapshot()

    with _lock:
        status = _read_status()
        status['running'] = True
        status['started_at'] = datetime.now().isoformat()
        status['current_run_id'] = run_id
        _write_status(status)

    t0 = time.time()
    error_msg = None
    tb_short = None
    try:
        from flv.pipeline import run_pipeline
        run_pipeline()
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        tb_short = traceback.format_exc()[-500:]
        _log(f'ERROR run_id={run_id}: {error_msg}')

    elapsed = time.time() - t0

    # Snapshot DEPOIS
    after = _get_freshness_snapshot()

    with _lock:
        status = _read_status()
        status['running'] = False
        status['duration_seconds'] = round(elapsed, 1)
        status['runs_total'] = (status.get('runs_total') or 0) + 1
        status.pop('current_run_id', None)
        if error_msg:
            status['last_error'] = error_msg
            status['last_error_at'] = datetime.now().isoformat()
            status['runs_failed'] = (status.get('runs_failed') or 0) + 1
        else:
            status['last_success'] = datetime.now().isoformat()
            status['last_error'] = None
            status['runs_success'] = (status.get('runs_success') or 0) + 1
        _write_status(status)

    # Registrar run
    run_record = {
        'run_id': run_id,
        'status': 'error' if error_msg else 'success',
        'trigger': trigger,
        'started_at': datetime.fromtimestamp(t0).isoformat(),
        'finished_at': datetime.now().isoformat(),
        'duration_seconds': round(elapsed, 1),
        'pid': os.getpid(),
        'hostname': platform.node(),
        'records_before': {k: v.get('count') if v else 0 for k, v in before.items()},
        'records_after': {k: v.get('count') if v else 0 for k, v in after.items()},
        'freshness_before': {k: v.get('max_date') if v else None for k, v in before.items()},
        'freshness_after': {k: v.get('max_date') if v else None for k, v in after.items()},
        'error': error_msg,
    }
    _append_run(run_record)

    status_word = 'SUCCESS' if not error_msg else 'FAILED'
    _log(f'{status_word} run_id={run_id} duration={round(elapsed,1)}s prices={after.get("prices",{}).get("max_date")} climate={after.get("climate",{}).get("max_date")}')

    return {
        'status': 'error' if error_msg else 'ok',
        'run_id': run_id,
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
        _log(f'LOOP mode started. Interval={hours}h')
        while True:
            run_pipeline_once(trigger=f'scheduler_{hours}h')
            time.sleep(hours * 3600)
    else:
        print('[Scheduler] Execução única')
        result = run_pipeline_once(trigger='cli_manual')
        print(json.dumps(result, ensure_ascii=False, indent=2))
