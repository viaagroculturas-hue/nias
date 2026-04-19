"""FLV Ensemble — blends Prophet + XGBoost forecasts weighted by recent MAPE.

Strategy:
1. Run both `prophet_model.predict()` and `xgb_model.predict()`.
2. Read rolling MAPE_30d per model from `flv_accuracy` and compute inverse-error
   weights: `w_i = (1 / mape_i) / sum(1 / mape_j)`.
3. Blend each forecast point: `p_ens = sum(w_i * p_i)`.
4. If either model is degraded (no-data / ETS fallback), use the non-degraded one
   standalone. If both are degraded, return the degraded one (Prophet preferred).

Registers a retrain callback so the `retrain_controller` can invalidate caches
and bump the model version when MAPE breaches thresholds.
"""
import time
from datetime import datetime

from flv.model.evaluator import rolling_mape
from flv.model.prophet_model import predict as prophet_predict
from flv.model.xgb_model import predict as xgb_predict

ENSEMBLE_VERSION = "ensemble-v1"
CACHE_TTL = 3600  # 1 hour, same as prophet_model cache

_cache = {}
_default_weights = {"prophet-v1": 0.5, "xgb-v1": 0.5}


def _model_weights(conn, culture_slug, terminal):
    """Compute inverse-MAPE weights per model_version over the last 30 days.

    Returns dict like {'prophet-v1': 0.6, 'xgb-v1': 0.4}. Falls back to equal
    weights when no accuracy rows exist yet.
    """
    candidates = ["prophet-v1", "xgb-v1", "gbr-v1"]
    mapes = {}
    for mv in candidates:
        m, n = rolling_mape(conn, culture_slug, terminal, 30, mv)
        if m is not None and n >= 3:
            mapes[mv] = max(m, 0.5)  # floor to avoid divide-by-zero boost
    if not mapes:
        return dict(_default_weights)

    inv = {mv: 1.0 / m for mv, m in mapes.items()}
    total = sum(inv.values())
    return {mv: v / total for mv, v in inv.items()}


def _blend(forecasts, weights):
    """forecasts = {model_version: forecast_list}. Returns blended forecast list."""
    # Index by date.
    by_date = {}
    for mv, lst in forecasts.items():
        w = weights.get(mv, 0.0)
        if w <= 0:
            continue
        for row in lst:
            d = row["date"]
            slot = by_date.setdefault(
                d, {"date": d, "price_w": 0.0, "lower_w": 0.0, "upper_w": 0.0, "w": 0.0}
            )
            slot["price_w"] += w * row["price"]
            slot["lower_w"] += w * row["lower"]
            slot["upper_w"] += w * row["upper"]
            slot["w"] += w

    out = []
    for d in sorted(by_date):
        s = by_date[d]
        if s["w"] <= 0:
            continue
        out.append(
            {
                "date": d,
                "price": round(s["price_w"] / s["w"], 2),
                "lower": round(s["lower_w"] / s["w"], 2),
                "upper": round(s["upper_w"] / s["w"], 2),
            }
        )
    return out


def predict(culture_slug, terminal=None, mun_id=None, horizon=None):
    """Ensemble prediction for (culture, terminal). Same dict shape as prophet_model.predict()."""
    cache_key = f"{culture_slug}_{terminal}_{mun_id}_{horizon}"
    now = time.time()
    cached = _cache.get(cache_key)
    if cached and now - cached[1] < CACHE_TTL:
        return cached[0]

    from flv.db import get_conn

    prophet_res = prophet_predict(culture_slug, terminal, mun_id, horizon)
    xgb_res = xgb_predict(culture_slug, terminal, mun_id, horizon)

    p_ok = bool(prophet_res.get("forecast")) and not prophet_res.get("degraded")
    x_ok = bool(xgb_res.get("forecast")) and not xgb_res.get("degraded")

    if not p_ok and not x_ok:
        # Both degraded — return prophet (ETS fallback or no-data) as-is.
        prophet_res["ensemble"] = False
        return prophet_res
    if p_ok and not x_ok:
        prophet_res["ensemble"] = False
        return prophet_res
    if x_ok and not p_ok:
        xgb_res["ensemble"] = False
        return xgb_res

    conn = get_conn()
    weights = _model_weights(conn, culture_slug, terminal)
    # Only consider models we actually have results for.
    active = {
        prophet_res["model"]: prophet_res["forecast"],
        xgb_res["model"]: xgb_res["forecast"],
    }
    active_weights = {mv: weights.get(mv, 0.5) for mv in active}
    total = sum(active_weights.values()) or 1.0
    active_weights = {mv: w / total for mv, w in active_weights.items()}

    blended = _blend(active, active_weights)
    if len(blended) >= 2:
        first = blended[0]["price"]
        last = blended[-1]["price"]
        pct = (last - first) / first * 100 if first > 0 else 0
        trend = "alta" if pct > 2 else ("baixa" if pct < -2 else "estavel")
    else:
        trend, pct = "estavel", 0

    # Confidence: weighted average of component confidences, bumped slightly by diversity.
    comp_conf = (
        prophet_res.get("confidence", 0) * active_weights.get(prophet_res["model"], 0)
        + xgb_res.get("confidence", 0) * active_weights.get(xgb_res["model"], 0)
    )
    confidence = min(95, int(round(comp_conf + 5)))

    result = {
        "culture": culture_slug,
        "model": ENSEMBLE_VERSION,
        "degraded": False,
        "horizon_days": horizon or prophet_res.get("horizon_days"),
        "trend": trend,
        "trend_pct": round(pct, 1),
        "confidence": confidence,
        "forecast": blended,
        "historical": prophet_res.get("historical") or xgb_res.get("historical") or [],
        "components": {
            "prophet": {
                "model": prophet_res["model"],
                "weight": round(active_weights.get(prophet_res["model"], 0), 3),
                "confidence": prophet_res.get("confidence", 0),
            },
            "xgb": {
                "model": xgb_res["model"],
                "weight": round(active_weights.get(xgb_res["model"], 0), 3),
                "confidence": xgb_res.get("confidence", 0),
            },
        },
        "ensemble": True,
        "generated_at": datetime.now().isoformat(),
    }
    _cache[cache_key] = (result, now)
    return result


def clear_cache(culture_slug=None, terminal=None):
    """Invalidate ensemble and per-model caches (used on retrain)."""
    from flv.model import prophet_model
    keys_to_drop = []
    if culture_slug is None:
        _cache.clear()
        try:
            prophet_model._cache.clear()
        except Exception:
            pass
        return
    prefix = f"{culture_slug}_{terminal}"
    for k in list(_cache.keys()):
        if k.startswith(prefix):
            keys_to_drop.append(k)
    for k in keys_to_drop:
        _cache.pop(k, None)
    try:
        for k in list(prophet_model._cache.keys()):
            if k.startswith(prefix):
                prophet_model._cache.pop(k, None)
    except Exception:
        pass


def run_all():
    """Persist ensemble predictions for all cultures × terminals into flv_predictions.

    Mirrors `prophet_model.run_all()` but writes `model_version='ensemble-v1'`,
    letting the evaluator score the ensemble separately from Prophet/XGB.
    """
    from flv.db import get_conn, query
    conn = get_conn()
    cultures = query("SELECT slug FROM flv_cultures")
    terminals = ["CEAGESP", "CEASA-PE", "CEASA-MG"]
    count = 0
    for c in cultures:
        for t in terminals:
            try:
                result = predict(c["slug"], t)
                if not result or not result.get("forecast"):
                    continue
                cid = conn.execute(
                    "SELECT id FROM flv_cultures WHERE slug=?", (c["slug"],)
                ).fetchone()
                if not cid:
                    continue
                for fc in result["forecast"]:
                    conn.execute(
                        "INSERT INTO flv_predictions "
                        "(culture_id,terminal,target_date,horizon_days,predicted_price,"
                        "price_lower_80,price_upper_80,trend_direction,confidence_pct,model_version) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (
                            cid["id"],
                            t,
                            fc["date"],
                            result["horizon_days"],
                            fc["price"],
                            fc["lower"],
                            fc["upper"],
                            result["trend"],
                            result["confidence"],
                            result["model"],
                        ),
                    )
                    count += 1
            except Exception as e:
                print(f"[FLV-Ensemble] erro {c['slug']}/{t}: {e}")
    conn.commit()
    return count


def _retrain_callback(culture_slug, terminal, model_version):
    """Called by retrain_controller when MAPE triggers. Invalidates caches and
    re-runs the ensemble so the next cycle emits fresh predictions.

    Returns (ok, mape_after). The actual retrain is stateless (we retrain every
    call), so this mostly clears caches and re-persists predictions.
    """
    from flv.db import get_conn
    from flv.model.evaluator import rolling_mape
    try:
        clear_cache(culture_slug, terminal)
        # Force a fresh prediction and persist it.
        result = predict(culture_slug, terminal)
        if not result or not result.get("forecast"):
            return False, None
        cid = get_conn().execute(
            "SELECT id FROM flv_cultures WHERE slug=?", (culture_slug,)
        ).fetchone()
        if cid:
            conn = get_conn()
            for fc in result["forecast"]:
                conn.execute(
                    "INSERT INTO flv_predictions "
                    "(culture_id,terminal,target_date,horizon_days,predicted_price,"
                    "price_lower_80,price_upper_80,trend_direction,confidence_pct,model_version) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        cid["id"],
                        terminal,
                        fc["date"],
                        result["horizon_days"],
                        fc["price"],
                        fc["lower"],
                        fc["upper"],
                        result["trend"],
                        result["confidence"],
                        result["model"],
                    ),
                )
            conn.commit()
        mape_after, _ = rolling_mape(get_conn(), culture_slug, terminal, 30, ENSEMBLE_VERSION)
        return True, mape_after
    except Exception as e:
        print(f"[FLV-Ensemble] retrain callback failed: {e}")
        return False, None


def register():
    """Register the retrain callback with retrain_controller."""
    from flv.model import retrain_controller
    retrain_controller.register_trainer(_retrain_callback)
