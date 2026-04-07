"""FLV Prophet Predictor — Time series forecasting with Prophet + ETS fallback."""
import time, json, math
from datetime import datetime, timedelta

_cache = {}  # {key: (result, timestamp)}
CACHE_TTL = 3600  # 1 hour

MIN_DATAPOINTS = 60
HORIZON_DAYS = 15

def predict(culture_slug, terminal=None, mun_id=None, horizon=None):
    """Run Prophet forecast for a culture. Returns dict with forecast, trend, confidence."""
    horizon = horizon or HORIZON_DAYS
    cache_key = f"{culture_slug}_{terminal}_{mun_id}_{horizon}"

    if cache_key in _cache:
        result, ts = _cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return result

    from flv.model.feature_builder import build_features, build_future_regressors
    features = build_features(culture_slug, terminal, mun_id)

    if len(features) < MIN_DATAPOINTS:
        result = _fallback_ets(features, horizon, culture_slug)
        _cache[cache_key] = (result, time.time())
        return result

    try:
        result = _run_prophet(features, horizon, culture_slug)
    except Exception as e:
        print(f'[FLV-Prophet] Prophet failed for {culture_slug}: {e}, falling back to ETS')
        result = _fallback_ets(features, horizon, culture_slug)

    _cache[cache_key] = (result, time.time())
    return result

def _run_prophet(features, horizon, culture_slug):
    """Run Prophet model with climate regressors."""
    try:
        from prophet import Prophet
        import numpy as np
    except ImportError:
        return _fallback_ets(features, horizon, culture_slug)

    import pandas as pd
    df = pd.DataFrame(features)
    df['ds'] = pd.to_datetime(df['ds'])

    # Log-transform for multiplicative behavior
    df['y_orig'] = df['y']
    df['y'] = np.log(df['y'].clip(lower=0.01))

    m = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode='multiplicative',
        changepoint_prior_scale=0.20,
        interval_width=0.80,
    )
    m.add_regressor('precip_7d')
    m.add_regressor('temp_max_avg')
    m.add_regressor('ndvi')
    m.add_regressor('is_holiday')
    m.fit(df[['ds', 'y', 'precip_7d', 'temp_max_avg', 'ndvi', 'is_holiday']])

    future = m.make_future_dataframe(periods=horizon)

    # Fill future regressors
    from flv.model.feature_builder import build_future_regressors
    future_regs = build_future_regressors(features, horizon)
    future_map = {r['ds']: r for r in future_regs}

    for col in ['precip_7d', 'temp_max_avg', 'ndvi', 'is_holiday']:
        last_val = df[col].iloc[-1]
        future[col] = future['ds'].apply(
            lambda d: future_map.get(d.strftime('%Y-%m-%d'), {}).get(col, last_val)
        )

    forecast = m.predict(future)

    # Back-transform
    for col in ['yhat', 'yhat_lower', 'yhat_upper']:
        forecast[col] = np.exp(forecast[col])

    # Extract forecast portion
    hist_len = len(df)
    fc_rows = forecast.iloc[hist_len:].to_dict('records')

    forecast_list = []
    for row in fc_rows:
        forecast_list.append({
            'date': row['ds'].strftime('%Y-%m-%d'),
            'price': round(row['yhat'], 2),
            'lower': round(row['yhat_lower'], 2),
            'upper': round(row['yhat_upper'], 2),
        })

    # Trend
    if len(forecast_list) >= 2:
        first = forecast_list[0]['price']
        last = forecast_list[-1]['price']
        pct = (last - first) / first * 100 if first > 0 else 0
        trend = 'alta' if pct > 2 else ('baixa' if pct < -2 else 'estavel')
    else:
        trend = 'estavel'
        pct = 0

    # Historical for chart
    historical = [{'date': f['ds'], 'price': f['y']} for f in features[-90:]]

    return {
        'culture': culture_slug,
        'model': 'prophet-v1',
        'degraded': False,
        'horizon_days': horizon,
        'trend': trend,
        'trend_pct': round(pct, 1),
        'confidence': 80,
        'forecast': forecast_list,
        'historical': historical,
        'generated_at': datetime.now().isoformat(),
    }

def _fallback_ets(features, horizon, culture_slug):
    """Simple exponential smoothing fallback when Prophet unavailable or insufficient data."""
    if not features:
        return {
            'culture': culture_slug, 'model': 'no-data', 'degraded': True,
            'horizon_days': horizon, 'trend': 'estavel', 'trend_pct': 0,
            'confidence': 0, 'forecast': [], 'historical': [],
            'generated_at': datetime.now().isoformat(),
        }

    prices = [f['y'] for f in features if f['y'] and f['y'] > 0]
    if not prices:
        return {
            'culture': culture_slug, 'model': 'no-data', 'degraded': True,
            'horizon_days': horizon, 'trend': 'estavel', 'trend_pct': 0,
            'confidence': 0, 'forecast': [], 'historical': [],
            'generated_at': datetime.now().isoformat(),
        }

    # Simple exponential smoothing
    alpha = 0.3
    level = prices[0]
    for p in prices[1:]:
        level = alpha * p + (1 - alpha) * level

    # Trend from last 7 values
    recent = prices[-min(7, len(prices)):]
    if len(recent) >= 2:
        trend_val = (recent[-1] - recent[0]) / len(recent)
    else:
        trend_val = 0

    last_date = datetime.strptime(features[-1]['ds'], '%Y-%m-%d')
    forecast_list = []
    for i in range(1, horizon + 1):
        dt = last_date + timedelta(days=i)
        pred = level + trend_val * i
        pred = max(pred, 0.01)
        forecast_list.append({
            'date': dt.strftime('%Y-%m-%d'),
            'price': round(pred, 2),
            'lower': round(pred * 0.85, 2),
            'upper': round(pred * 1.15, 2),
        })

    pct = (forecast_list[-1]['price'] - prices[-1]) / prices[-1] * 100 if prices[-1] > 0 else 0
    trend = 'alta' if pct > 2 else ('baixa' if pct < -2 else 'estavel')

    historical = [{'date': f['ds'], 'price': f['y']} for f in features[-90:]]

    return {
        'culture': culture_slug,
        'model': 'ets-fallback',
        'degraded': True,
        'horizon_days': horizon,
        'trend': trend,
        'trend_pct': round(pct, 1),
        'confidence': 45,
        'forecast': forecast_list,
        'historical': historical,
        'generated_at': datetime.now().isoformat(),
    }

def run_all():
    """Run predictions for all 16 cultures × main terminals."""
    from flv.db import get_conn, query
    conn = get_conn()
    cultures = query("SELECT slug FROM flv_cultures")
    terminals = ['CEAGESP', 'CEASA-PE', 'CEASA-MG']
    count = 0

    for c in cultures:
        for t in terminals:
            try:
                result = predict(c['slug'], t)
                if result and result.get('forecast'):
                    # Store predictions
                    cid = conn.execute("SELECT id FROM flv_cultures WHERE slug=?", (c['slug'],)).fetchone()
                    if cid:
                        for fc in result['forecast']:
                            conn.execute(
                                "INSERT OR REPLACE INTO flv_predictions (culture_id,terminal,target_date,horizon_days,predicted_price,price_lower_80,price_upper_80,trend_direction,confidence_pct,model_version) "
                                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (cid['id'], t, fc['date'], result['horizon_days'],
                                 fc['price'], fc['lower'], fc['upper'],
                                 result['trend'], result['confidence'], result['model'])
                            )
                    count += 1
            except Exception as e:
                print(f'[FLV-Prophet] Error {c["slug"]}/{t}: {e}')

    conn.commit()
    print(f'[FLV-Prophet] {count} previsoes geradas')
    return count
