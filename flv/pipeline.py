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

    # 4b. Macro indicators (BCB PTAX/Selic/IPCA + ANP diesel)
    try:
        from flv.collectors.macro import fetch_all as macro_fetch
        macro_fetch()
    except Exception as e:
        print(f'[FLV-Pipeline] Macro erro: {e}')

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

    # 6b. Run ensemble (Prophet + XGBoost) predictions
    try:
        from flv.model.ensemble import run_all as ensemble_run_all, register as ensemble_register
        ensemble_register()  # register retrain callback before retrain controller runs
        n = ensemble_run_all()
        print(f'[FLV-Pipeline] Ensemble: {n} predicoes persistidas')
    except Exception as e:
        print(f'[FLV-Pipeline] Ensemble erro: {e}')

    # 7. Feedback loop: score past predictions vs observed prices
    try:
        from flv.model.evaluator import evaluate_predictions
        n = evaluate_predictions()
        print(f'[FLV-Pipeline] Evaluator: {n} predicoes avaliadas')
    except Exception as e:
        print(f'[FLV-Pipeline] Evaluator erro: {e}')

    # 8. Retrain controller: log triggers when MAPE exceeds thresholds
    try:
        from flv.model.retrain_controller import run as retrain_run
        res = retrain_run()
        if res['triggers']:
            print(f'[FLV-Pipeline] Retrain: {len(res["triggers"])} triggers ({[t["culture_slug"] for t in res["triggers"]]})')
    except Exception as e:
        print(f'[FLV-Pipeline] Retrain erro: {e}')

    # 9. Pilar 4.A (CV): satellite scene metadata + LULC stats + crop classifier
    try:
        from flv.collectors.sentinel_stac import fetch_all as sentinel_fetch
        sentinel_fetch(limit_muns=20)  # throttle: 20 muns x 3 platforms = 60 STAC calls/cycle
    except Exception as e:
        print(f'[FLV-Pipeline] Sentinel STAC erro: {e}')

    try:
        from flv.collectors.lulc import fetch_all as lulc_fetch
        lulc_fetch()
    except Exception as e:
        print(f'[FLV-Pipeline] LULC erro: {e}')

    try:
        from flv.cv.crop_classifier import register as cv_register, run_all as cv_run_all
        cv_register()
        n = cv_run_all()
        print(f'[FLV-Pipeline] CV Classifier: {n} classificacoes persistidas')
    except Exception as e:
        print(f'[FLV-Pipeline] CV erro: {e}')

    # 9d. Pilar 4.B: yield regression
    try:
        from flv.cv.yield_model import run_all as yield_run
        n = yield_run()
        print(f'[FLV-Pipeline] Yield Model: {n} previsoes de produtividade')
    except Exception as e:
        print(f'[FLV-Pipeline] Yield erro: {e}')

    # 9e. Pilar 4.B: change-detection (anomalies)
    try:
        from flv.cv.change_detection import run_all as cd_run
        n = cd_run()
        print(f'[FLV-Pipeline] Change-Detect: {n} anomalias')
    except Exception as e:
        print(f'[FLV-Pipeline] Change-detect erro: {e}')

    elapsed = time.time() - t0
    print(f'[FLV-Pipeline] Ciclo completo em {elapsed:.1f}s')
