"""FLV CV Yield Model — Pilar 4.B.

Estimates per-municipality per-crop productivity (ton/ha) from a compact,
CPU-friendly feature set:

  * NDVI peak in the target season (strongest yield signal for row crops)
  * Growing Degree Days (GDD) accumulated from flv_climate
  * Heat-stress day count (temp_max ≥ 35 °C)
  * Total precipitation
  * LULC prior for the target crop (as area_pct)
  * USD/BRL and IPCA year-mean (proxies for input cost inflation)

The model is a scikit-learn GradientBoostingRegressor trained on the ground
truth we already have in flv_production (SIDRA PAM tons + area_ha). When the
repo has <12 samples for a given crop, the estimator falls back to a
climatology-adjusted prior so callers always get a numeric answer.
"""
from __future__ import annotations

import json
import math
import os
import pickle
import statistics
import threading

MODEL_VERSION = "gbr-yield-v1"
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "flv_cv_yield_gbr.pkl",
)

FEATURE_NAMES = [
    "lat", "abs_lat",
    "ndvi_peak", "ndvi_mean", "ndvi_std",
    "gdd_total", "heat_stress_days", "precip_total",
    "lulc_crop_pct",
    "usd_mean", "ipca_mean",
]

# Climatology priors (ton/ha) used when the learned model can't fit. Values are
# intentionally conservative — real SIDRA observations override them at train time.
DEFAULT_YIELD_PRIORS = {
    "soja": 3.4, "milho": 5.6, "tomate": 65.0, "banana": 14.5,
    "laranja": 22.0, "cana": 75.0, "arroz": 5.0, "feijao": 1.2,
    "pastagem": 0.0, "floresta": 0.0,
}

_MODEL_LOCK = threading.Lock()
_MODEL_CACHE: dict = {"gbr": None, "trained_at": None, "samples": 0, "per_crop_bias": {}}


# ---------------------------------------------------------------------------
# Feature extraction (uses already-collected data; no new HTTP calls here)
# ---------------------------------------------------------------------------
def extract(conn, mun_id: int, culture_slug: str, year: int) -> dict:
    """Return an ORDERED feature dict (keys = FEATURE_NAMES)."""
    feats = {n: 0.0 for n in FEATURE_NAMES}
    mun = conn.execute(
        "SELECT lat, lon FROM flv_municipalities WHERE id = ?", (mun_id,)
    ).fetchone()
    if mun:
        feats["lat"] = mun["lat"] or 0.0
        feats["abs_lat"] = abs(mun["lat"] or 0.0)

    _fill_ndvi(conn, mun_id, year, feats)
    _fill_climate(conn, mun_id, year, feats)
    _fill_lulc_for_crop(conn, mun_id, year, culture_slug, feats)
    _fill_macro(conn, year, feats)
    return feats


def extract_vector(conn, mun_id: int, culture_slug: str, year: int) -> list:
    f = extract(conn, mun_id, culture_slug, year)
    return [f[n] for n in FEATURE_NAMES]


def _fill_ndvi(conn, mun_id, year, feats):
    rows = conn.execute(
        "SELECT ndvi_value FROM flv_ndvi WHERE mun_id = ? AND obs_date LIKE ?",
        (mun_id, f"{year}%"),
    ).fetchall()
    values = [r["ndvi_value"] for r in rows if r["ndvi_value"] is not None]
    if not values:
        return
    feats["ndvi_peak"] = max(values)
    feats["ndvi_mean"] = sum(values) / len(values)
    feats["ndvi_std"] = statistics.pstdev(values) if len(values) > 1 else 0.0


def _fill_climate(conn, mun_id, year, feats):
    rows = conn.execute(
        """
        SELECT temp_max_c, temp_min_c, precip_mm FROM flv_climate
        WHERE mun_id = ? AND obs_date LIKE ?
        """,
        (mun_id, f"{year}%"),
    ).fetchall()
    if not rows:
        return
    gdd = 0.0
    heat = 0
    precip = 0.0
    base = 10.0  # GDD base temp (typical for row crops)
    for r in rows:
        tmax = r["temp_max_c"]
        tmin = r["temp_min_c"]
        p = r["precip_mm"] or 0.0
        precip += p
        if tmax is not None and tmin is not None:
            tmean = (tmax + tmin) / 2.0
            gdd += max(0.0, tmean - base)
            if tmax >= 35.0:
                heat += 1
    feats["gdd_total"] = gdd
    feats["heat_stress_days"] = float(heat)
    feats["precip_total"] = precip


def _fill_lulc_for_crop(conn, mun_id, year, culture_slug, feats):
    row = conn.execute(
        """
        SELECT area_pct FROM flv_lulc_stats
        WHERE mun_id = ? AND year = ? AND crop_class = ?
        ORDER BY area_pct DESC LIMIT 1
        """,
        (mun_id, year, culture_slug),
    ).fetchone()
    if row:
        feats["lulc_crop_pct"] = float(row["area_pct"] or 0.0)
        return
    # Fallback to any prior year we have.
    row = conn.execute(
        """
        SELECT area_pct FROM flv_lulc_stats
        WHERE mun_id = ? AND crop_class = ? AND year < ?
        ORDER BY year DESC LIMIT 1
        """,
        (mun_id, culture_slug, year),
    ).fetchone()
    if row:
        feats["lulc_crop_pct"] = float(row["area_pct"] or 0.0)


def _fill_macro(conn, year, feats):
    row = conn.execute(
        """
        SELECT series, AVG(value) AS m FROM flv_macro
        WHERE obs_date LIKE ? AND series IN ('usd_brl','ipca_yoy')
        GROUP BY series
        """,
        (f"{year}%",),
    ).fetchall()
    for r in row:
        if r["series"] == "usd_brl":
            feats["usd_mean"] = float(r["m"] or 0.0)
        elif r["series"] == "ipca_yoy":
            feats["ipca_mean"] = float(r["m"] or 0.0)


# ---------------------------------------------------------------------------
# Dataset assembly from flv_production (SIDRA PAM ground truth)
# ---------------------------------------------------------------------------
def dataset(conn, min_area_ha: float = 10.0):
    """Build (X, y, meta) where y = production_tons / area_harvested_ha.

    Skips rows with area_harvested_ha < min_area_ha (statistical noise).
    """
    rows = conn.execute(
        """
        SELECT p.mun_id AS mun_id, c.slug AS culture_slug, p.year AS year,
               p.production_tons AS tons, p.area_harvested_ha AS area_ha
        FROM flv_production p
        JOIN flv_cultures c ON c.id = p.culture_id
        WHERE p.production_tons IS NOT NULL
          AND p.area_harvested_ha IS NOT NULL
          AND p.area_harvested_ha >= ?
        """,
        (min_area_ha,),
    ).fetchall()
    X, y, meta = [], [], []
    for r in rows:
        tons = float(r["tons"] or 0.0)
        area = float(r["area_ha"] or 0.0)
        if area <= 0 or tons <= 0:
            continue
        yld = tons / area
        if yld <= 0 or yld > 500:  # reject obvious outliers
            continue
        vec = extract_vector(conn, r["mun_id"], r["culture_slug"], r["year"])
        X.append(vec)
        y.append(yld)
        meta.append({"mun_id": r["mun_id"], "culture_slug": r["culture_slug"], "year": r["year"]})
    return X, y, meta


# ---------------------------------------------------------------------------
# Training + inference
# ---------------------------------------------------------------------------
def _load_sklearn():
    try:
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.metrics import mean_absolute_percentage_error
    except ImportError as e:
        raise RuntimeError(
            "scikit-learn is required for the CV yield model; "
            "add scikit-learn>=1.3 to requirements_flv.txt"
        ) from e
    return GradientBoostingRegressor, mean_absolute_percentage_error


def train_and_persist(conn=None, min_samples: int = 12):
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()

    X, y, meta = dataset(conn)
    if len(X) < min_samples:
        return {
            "status": "insufficient_data",
            "samples": len(X),
            "model_version": MODEL_VERSION,
        }

    GBR, mape = _load_sklearn()
    clf = GBR(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        loss="huber",
        random_state=42,
    )
    clf.fit(X, y)

    # Per-crop bias to recover for culture whose class distribution is tiny.
    per_crop_bias: dict = {}
    preds = clf.predict(X)
    for p, actual, m in zip(preds, y, meta):
        per_crop_bias.setdefault(m["culture_slug"], []).append(actual - float(p))
    per_crop_bias = {k: float(sum(v) / len(v)) for k, v in per_crop_bias.items() if v}

    with _MODEL_LOCK:
        _MODEL_CACHE["gbr"] = clf
        _MODEL_CACHE["per_crop_bias"] = per_crop_bias
        _MODEL_CACHE["samples"] = len(X)

    try:
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({"gbr": clf, "bias": per_crop_bias,
                         "feature_names": FEATURE_NAMES,
                         "model_version": MODEL_VERSION}, f)
    except Exception as e:
        print(f"[FLV-Yield] Nao foi possivel persistir modelo: {e}")

    in_sample_mape = float(mape(y, preds)) * 100
    return {
        "status": "trained",
        "samples": len(X),
        "crops_with_bias": len(per_crop_bias),
        "mape_in_sample_pct": round(in_sample_mape, 3),
        "model_version": MODEL_VERSION,
    }


def _load_if_needed():
    if _MODEL_CACHE.get("gbr") is not None:
        return
    if not os.path.exists(MODEL_PATH):
        return
    try:
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        with _MODEL_LOCK:
            _MODEL_CACHE["gbr"] = data.get("gbr")
            _MODEL_CACHE["per_crop_bias"] = data.get("bias") or {}
    except Exception as e:
        print(f"[FLV-Yield] Falha ao carregar modelo em disco: {e}")


def predict_one(conn, mun_id: int, culture_slug: str, year: int) -> dict:
    """Return a dict with yield_ton_ha, lower/upper and the feature vector used.

    Falls back to DEFAULT_YIELD_PRIORS * LULC scaling when the learned model
    isn't available, so the API never returns empty responses.
    """
    _load_if_needed()
    feats = extract(conn, mun_id, culture_slug, year)
    vec = [feats[n] for n in FEATURE_NAMES]

    gbr = _MODEL_CACHE.get("gbr")
    bias = _MODEL_CACHE.get("per_crop_bias") or {}
    if gbr is not None:
        base = float(gbr.predict([vec])[0])
        adj = base + bias.get(culture_slug, 0.0)
        yld = max(0.0, adj)
        # Heuristic IC: ±15% around the point (conservative).
        lower = max(0.0, yld * 0.85)
        upper = yld * 1.15
        source = "gbr"
    else:
        prior = DEFAULT_YIELD_PRIORS.get(culture_slug, 0.0)
        # Scale down if NDVI peak is low or LULC share is tiny.
        ndvi_adj = min(1.0, max(0.2, feats["ndvi_peak"] / 0.7)) if feats["ndvi_peak"] > 0 else 0.6
        lulc_adj = min(1.0, max(0.3, feats["lulc_crop_pct"] * 3.0)) if feats["lulc_crop_pct"] > 0 else 0.7
        yld = prior * ndvi_adj * lulc_adj
        lower = yld * 0.70
        upper = yld * 1.30
        source = "prior"

    return {
        "mun_id": mun_id,
        "culture_slug": culture_slug,
        "year": year,
        "yield_ton_ha": float(round(yld, 3)),
        "yield_lower": float(round(lower, 3)),
        "yield_upper": float(round(upper, 3)),
        "ndvi_peak": float(round(feats["ndvi_peak"], 3)),
        "gdd_total": float(round(feats["gdd_total"], 1)),
        "features": feats,
        "model_version": MODEL_VERSION,
        "source": source,
    }


def predict_all(conn=None, year: int = None, cultures: list = None):
    """Persist yield predictions for all (mun, culture) combos for a given year."""
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()
    if year is None:
        row = conn.execute(
            "SELECT MAX(year) AS y FROM flv_lulc_stats"
        ).fetchone()
        year = row["y"] if row and row["y"] else 2024

    if cultures is None:
        rows = conn.execute("SELECT slug FROM flv_cultures").fetchall()
        cultures = [r["slug"] for r in rows]

    muns = conn.execute("SELECT id FROM flv_municipalities").fetchall()
    count = 0
    for m in muns:
        for crop in cultures:
            try:
                pred = predict_one(conn, m["id"], crop, year)
            except Exception as e:
                print(f"[FLV-Yield] Erro mun={m['id']} crop={crop}: {e}")
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO flv_yield_predictions
                (mun_id, culture_slug, year, yield_ton_ha, yield_lower, yield_upper,
                 ndvi_peak, gdd_total, features_json, model_version, predicted_at)
                VALUES (?,?,?,?,?,?,?,?,?,?, datetime('now'))
                """,
                (
                    m["id"], crop, year,
                    pred["yield_ton_ha"], pred["yield_lower"], pred["yield_upper"],
                    pred["ndvi_peak"], pred["gdd_total"],
                    json.dumps(pred["features"]),
                    MODEL_VERSION,
                ),
            )
            count += 1
    conn.commit()
    print(f"[FLV-Yield] {count} previsoes de produtividade persistidas (year={year})")
    return count


def run_all():
    """Pipeline entrypoint: train (best effort) + predict_all()."""
    from flv.db import get_conn
    conn = get_conn()
    try:
        train_and_persist(conn)
    except Exception as e:
        print(f"[FLV-Yield] Treino falhou, usando priors: {e}")
    return predict_all(conn)
