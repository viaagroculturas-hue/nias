"""FLV Pipeline Orchestrator — Runs all collectors and models in sequence."""
import time, traceback

def run_pipeline():
    """Execute full data pipeline: collect → model → alerts."""
    print('[FLV-Pipeline] Iniciando ciclo de coleta...')
    t0 = time.time()

    # 1. SIDRA production (annual, skip if fresh)
    try:
        from flv.collectors.sidra import fetch_all as sidra_fetch
        sidra_fetch()
    except Exception as e:
        print(f'[FLV-Pipeline] SIDRA erro: {e}')

    # 2. INMET/Open-Meteo climate — Brasil (municípios existentes)
    try:
        from flv.collectors.inmet import fetch_all as inmet_fetch
        inmet_fetch()
    except Exception as e:
        print(f'[FLV-Pipeline] INMET erro: {e}')

    # 2.5 Open-Meteo batch — América do Sul (44 polos, 1 request)
    try:
        import sqlite3
        from flv.paths import get_db_path
        from flv.sa_weather_persistence import run_south_america_weather_cycle
        _sa_conn = sqlite3.connect(str(get_db_path()), check_same_thread=False, timeout=10)
        _sa_conn.row_factory = sqlite3.Row
        _sa_conn.execute("PRAGMA journal_mode=WAL")
        sa_result = run_south_america_weather_cycle(_sa_conn)
        _sa_conn.close()
        print(f'[FLV-Pipeline] SA Weather: status={sa_result.get("status")} inserted={sa_result.get("inserted", 0)}')
    except Exception as e:
        print(f'[FLV-Pipeline] SA Weather erro: {e}')

    # 3. NDVI satellite data
    try:
        from flv.collectors.satveg import fetch_all as ndvi_fetch
        ndvi_fetch()
    except Exception as e:
        print(f'[FLV-Pipeline] NDVI erro: {e}')

    # 4. CEASA prices (CONAB)
    try:
        from flv.collectors.ceasa import fetch_all as ceasa_fetch
        ceasa_fetch()
    except Exception as e:
        print(f'[FLV-Pipeline] CEASA erro: {e}')

    # 4.5 Macro indicators (economia/energia) — importante para custo/logística
    try:
        from flv.collectors.macro import coletar_indicadores_macro
        coletar_indicadores_macro()
    except Exception as e:
        print(f'[FLV-Pipeline] Macro erro: {e}')

    # 4.6 Notícias (NLP) → índice de risco agregado
    try:
        from flv.collectors.news_risk import coletar_indice_risco_noticias
        coletar_indice_risco_noticias()
    except Exception as e:
        print(f'[FLV-Pipeline] NewsRisk erro: {e}')

    # 4.7 Teleconexões (El Niño/Atlântico Norte) → clima global
    try:
        from flv.collectors.teleconnections import coletar_teleconexoes_globais
        coletar_teleconexoes_globais()
    except Exception as e:
        print(f'[FLV-Pipeline] Teleconexões erro: {e}')

    # 5. Evaluate anticipation thresholds
    try:
        from flv.model.thresholds import evaluate_realtime
        evaluate_realtime()
    except Exception as e:
        print(f'[FLV-Pipeline] Thresholds erro: {e}')

    # 6. Run Prophet predictions
    try:
        from flv.model.prophet_model import run_all
        run_all()
    except Exception as e:
        print(f'[FLV-Pipeline] Prophet erro: {e}')

    elapsed = time.time() - t0
    print(f'[FLV-Pipeline] Ciclo completo em {elapsed:.1f}s')
