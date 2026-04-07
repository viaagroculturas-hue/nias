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

    # 2. INMET/Open-Meteo climate (7 days)
    try:
        from flv.collectors.inmet import fetch_all as inmet_fetch
        inmet_fetch()
    except Exception as e:
        print(f'[FLV-Pipeline] INMET erro: {e}')

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
