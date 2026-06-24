"""
FLV Paths — Centraliza caminhos de dados, banco e logs.
========================================================
Todos os módulos do projeto devem usar estas funções em vez de construir
caminhos manualmente. Suporta variáveis de ambiente para produção (Render).
"""
import os
from pathlib import Path

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_data_dir() -> Path:
    """Diretório principal de dados. Criado automaticamente se não existir."""
    path = Path(os.environ.get('NIAS_DATA_DIR', str(_ROOT / 'data')))
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_db_path() -> Path:
    """Caminho do banco SQLite principal."""
    env = os.environ.get('NIAS_DB_PATH')
    if env:
        return Path(env)
    return get_data_dir() / 'nia_flv.db'


def get_pipeline_status_path() -> Path:
    """Caminho do arquivo de status do pipeline."""
    env = os.environ.get('NIAS_PIPELINE_STATUS_PATH')
    if env:
        return Path(env)
    return get_data_dir() / 'pipeline_status.json'


def get_pipeline_runs_path() -> Path:
    """Caminho do histórico de execuções do pipeline (JSONL)."""
    return get_data_dir() / 'pipeline_runs.jsonl'


def get_scheduler_log_path() -> Path:
    """Caminho do log do scheduler."""
    env = os.environ.get('NIAS_SCHEDULER_LOG_PATH')
    if env:
        return Path(env)
    return get_data_dir() / 'scheduler.log'


def get_storage_info() -> dict:
    """Informações sobre o storage atual para endpoints de observabilidade."""
    data_dir = get_data_dir()
    db_path = get_db_path()

    # Detectar se é persistente (Render Persistent Disk)
    is_render = bool(os.environ.get('RENDER'))
    has_data_dir_env = bool(os.environ.get('NIAS_DATA_DIR'))
    # Render persistent disk monta em /opt/render/project/src/data ou similar
    persistent = has_data_dir_env and is_render
    # Local é sempre persistente
    if not is_render:
        persistent = True

    return {
        'type': 'sqlite',
        'path': str(db_path),
        'data_dir': str(data_dir),
        'db_exists': db_path.exists(),
        'db_size_mb': round(db_path.stat().st_size / 1048576, 2) if db_path.exists() else 0,
        'persistent': persistent,
        'environment': 'render' if is_render else 'local',
        'env_configured': has_data_dir_env,
    }
