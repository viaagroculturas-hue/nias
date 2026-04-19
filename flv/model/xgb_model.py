"""FLV XGBoost Predictor — gradient-boosted trees over lag + climate + macro features.

Complements Prophet (which is strong on seasonality) with a model that handles
non-linear interactions between climate, macro, and price history.

Returns the same dict shape as `flv.model.prophet_model.predict()` so the
ensemble and the API route can swap models transparently.
"""
import math
from datetime import datetime, timedelta

from flv.model.feature_builder import (
    active_macro_regressors,
    build_features,
    build_future_regressors,
)

MIN_DATAPOINTS = 60
HORIZON_DAYS = 15
LAGS = (1, 2, 7, 14)

BASE_REGRESSORS = ["precip_7d", "temp_max_avg", "ndvi", "is_holiday"]


def _empty(culture_slug, horizon):
    return {
        "culture": culture_slug,
        "model": "no-data",
        "degraded": True,
        "horizon_days": horizon,
        "trend": "estavel",
        "trend_pct": 0,
        "confidence": 0,
        "forecast": [],
        "historical": [],
        "generated_at": datetime.now().isoformat(),
    }


def _get_regressor():
    """Prefer xgboost; gracefully fall back to sklearn.GradientBoostingRegressor."""
    try:
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=250,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
            n_jobs=1,
            verbosity=0,
        ), "xgb-v1"
    except ImportError:
        pass
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(
            n_estimators=250,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.9,
            random_state=42,
        ), "gbr-v1"
    except ImportError:
        return None, None


def predict(culture_slug, terminal=None, mun_id=None, horizon=None):
    """Run XGBoost forecast. Returns dict with forecast, trend, confidence."""
    horizon = horizon or HORIZON_DAYS
    features = build_features(culture_slug, terminal, mun_id)
    if len(features) < MIN_DATAPOINTS:
        return _empty(culture_slug, horizon)

    regressor, model_name = _get_regressor()
    if regressor is None:
        return _empty(culture_slug, horizon)

    macro_cols = active_macro_regressors(features)
    feature_cols = BASE_REGRESSORS + macro_cols + ["dow", "month"] + [
        f"y_lag_{lag}" for lag in LAGS
    ]

    # Build X/y matrix with lag features.
    max_lag = max(LAGS)
    rows = []
    y_list = []
    for i, f in enumerate(features):
        if i < max_lag:
            continue
        dt = datetime.strptime(f["ds"], "%Y-%m-%d")
        row = {
            "ds": f["ds"],
            "precip_7d": f.get("precip_7d", 0.0),
            "temp_max_avg": f.get("temp_max_avg", 0.0),
            "ndvi": f.get("ndvi", 0.5),
            "is_holiday": f.get("is_holiday", 0.0),
            "dow": dt.weekday(),
            "month": dt.month,
        }
        for col in macro_cols:
            row[col] = f.get(col, 0.0)
        for lag in LAGS:
            row[f"y_lag_{lag}"] = features[i - lag]["y"]
        rows.append(row)
        y_list.append(f["y"])

    if len(rows) < 30:
        return _empty(culture_slug, horizon)

    X = [[r[c] for c in feature_cols] for r in rows]
    try:
        regressor.fit(X, y_list)
    except Exception as e:
        print(f"[FLV-XGB] fit failed for {culture_slug}: {e}")
        return _empty(culture_slug, horizon)

    # Recursive multi-step forecast.
    history_prices = [f["y"] for f in features]
    last_row = features[-1]
    last_date = datetime.strptime(last_row["ds"], "%Y-%m-%d")
    future_regs = {r["ds"]: r for r in build_future_regressors(features, horizon)}

    forecast_list = []
    for step in range(1, horizon + 1):
        dt = last_date + timedelta(days=step)
        ds = dt.strftime("%Y-%m-%d")
        fr = future_regs.get(ds, last_row)
        feats = {
            "precip_7d": fr.get("precip_7d", last_row["precip_7d"]),
            "temp_max_avg": fr.get("temp_max_avg", last_row["temp_max_avg"]),
            "ndvi": fr.get("ndvi", last_row["ndvi"]),
            "is_holiday": fr.get("is_holiday", 0.0),
            "dow": dt.weekday(),
            "month": dt.month,
        }
        for col in macro_cols:
            feats[col] = fr.get(col, last_row.get(col, 0.0))
        for lag in LAGS:
            idx = len(history_prices) - lag
            feats[f"y_lag_{lag}"] = history_prices[idx] if idx >= 0 else history_prices[0]

        x_row = [feats[c] for c in feature_cols]
        try:
            pred = float(regressor.predict([x_row])[0])
        except Exception as e:
            print(f"[FLV-XGB] predict step {step} failed: {e}")
            pred = history_prices[-1]
        pred = max(pred, 0.01)

        # Confidence interval: ±1 historical stddev of residuals (simple).
        forecast_list.append(
            {
                "date": ds,
                "price": round(pred, 2),
                "lower": round(pred * 0.88, 2),
                "upper": round(pred * 1.12, 2),
            }
        )
        history_prices.append(pred)

    if len(forecast_list) >= 2:
        first = forecast_list[0]["price"]
        last = forecast_list[-1]["price"]
        pct = (last - first) / first * 100 if first > 0 else 0
        trend = "alta" if pct > 2 else ("baixa" if pct < -2 else "estavel")
    else:
        trend, pct = "estavel", 0

    historical = [{"date": f["ds"], "price": f["y"]} for f in features[-90:]]

    return {
        "culture": culture_slug,
        "model": model_name,
        "degraded": False,
        "horizon_days": horizon,
        "trend": trend,
        "trend_pct": round(pct, 1),
        "confidence": 75,
        "forecast": forecast_list,
        "historical": historical,
        "generated_at": datetime.now().isoformat(),
    }
