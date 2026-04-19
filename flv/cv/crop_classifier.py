"""FLV CV Crop Classifier — RandomForest over multi-source features.

Trains on (X, y) assembled by feature_extractor.dataset() and persists
predictions into flv_crop_classification. Designed to run on CPU only; no
deep learning, no GPU, no heavy tile I/O.

The classifier lifecycle:

  train_and_persist()   — retrain on latest LULC labels; store model in-memory.
  predict_one(mun, y)   — single-record inference (returns label + top-k).
  predict_all(year)     — batch inference for every municipality; writes to
                          flv_crop_classification.
  register()            — hook into the retrain_controller (Pilar 3) so CV
                          accuracy degradation triggers retraining.

The MODEL_VERSION string is what lands in flv_crop_classification.model_version
and is what the Pilar 3 retrain controller uses to scope triggers.
"""
import json
import math
import os
import pickle
import threading

from flv.cv import feature_extractor as fe

MODEL_VERSION = "rf-cv-v1"
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "flv_cv_rf.pkl",
)

_MODEL_LOCK = threading.Lock()
_MODEL_CACHE = {"clf": None, "classes": None, "trained_at": None}


def _load_sklearn():
    """Lazy import so tests that don't exercise the model don't require sklearn."""
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, f1_score
    except ImportError as e:
        raise RuntimeError(
            "scikit-learn is required for the CV classifier; "
            "add scikit-learn>=1.3 to requirements_flv.txt"
        ) from e
    return RandomForestClassifier, accuracy_score, f1_score


def train_and_persist(conn=None, min_samples=8):
    """Train RandomForest on available (mun, year) → crop labels.

    Returns a dict with metrics; raises if not enough labeled data.
    """
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()

    X, y, meta = fe.dataset(conn)
    if len(X) < min_samples or len(set(y)) < 2:
        return {
            "status": "insufficient_data",
            "samples": len(X),
            "classes": len(set(y)),
            "model_version": MODEL_VERSION,
        }

    RandomForestClassifier, accuracy_score, f1_score = _load_sklearn()
    clf = RandomForestClassifier(
        n_estimators=80,
        max_depth=10,
        min_samples_leaf=2,
        n_jobs=1,
        random_state=42,
        class_weight="balanced",
    )
    clf.fit(X, y)

    # In-sample metrics: this is a small-N weakly-supervised pipeline — holding
    # out a test set would typically leave < 3 samples. The Pilar 3 evaluator
    # later measures real-world error via flv_cv_accuracy (PR#6).
    y_hat = clf.predict(X)
    acc = float(accuracy_score(y, y_hat))
    f1 = float(f1_score(y, y_hat, average="macro"))

    with _MODEL_LOCK:
        _MODEL_CACHE["clf"] = clf
        _MODEL_CACHE["classes"] = list(clf.classes_)
        _MODEL_CACHE["trained_at"] = _now()

    try:
        with open(MODEL_PATH, "wb") as f:
            pickle.dump({"clf": clf, "classes": list(clf.classes_),
                         "feature_names": fe.FEATURE_NAMES,
                         "model_version": MODEL_VERSION}, f)
    except Exception as e:
        print(f"[FLV-CV] Nao foi possivel persistir modelo: {e}")

    return {
        "status": "trained",
        "samples": len(X),
        "classes": _MODEL_CACHE["classes"],
        "accuracy_in_sample": round(acc, 4),
        "f1_macro_in_sample": round(f1, 4),
        "model_version": MODEL_VERSION,
    }


def _load_model_if_needed():
    if _MODEL_CACHE["clf"] is not None:
        return
    if not os.path.exists(MODEL_PATH):
        return
    try:
        with open(MODEL_PATH, "rb") as f:
            data = pickle.load(f)
        with _MODEL_LOCK:
            _MODEL_CACHE["clf"] = data.get("clf")
            _MODEL_CACHE["classes"] = data.get("classes") or []
    except Exception as e:
        print(f"[FLV-CV] Falha ao carregar modelo em disco: {e}")


def predict_one(conn, mun_id, year):
    """Predict for a single (mun, year). Returns dict or None if no model."""
    _load_model_if_needed()
    clf = _MODEL_CACHE.get("clf")
    if clf is None:
        return None
    vec = fe.extract_vector(conn, mun_id, year)
    proba = clf.predict_proba([vec])[0]
    classes = list(clf.classes_)
    top = sorted(zip(classes, proba), key=lambda t: t[1], reverse=True)
    top_k = {c: float(round(p, 4)) for c, p in top[:5]}
    return {
        "mun_id": mun_id,
        "year": year,
        "predicted_crop": top[0][0],
        "confidence": float(round(top[0][1], 4)),
        "top_k": top_k,
        "features": dict(zip(fe.FEATURE_NAMES, vec)),
        "model_version": MODEL_VERSION,
    }


def predict_all(conn=None, year=None):
    """Run inference for every municipality and persist to flv_crop_classification.

    Returns the number of rows upserted.
    """
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()
    _load_model_if_needed()
    if _MODEL_CACHE.get("clf") is None:
        # Auto-train on first use if we have data.
        res = train_and_persist(conn)
        if res.get("status") != "trained":
            return 0

    if year is None:
        row = conn.execute("SELECT MAX(year) AS y FROM flv_lulc_stats").fetchone()
        year = row["y"] if row and row["y"] else 2024

    muns = conn.execute("SELECT id FROM flv_municipalities").fetchall()
    count = 0
    for m in muns:
        try:
            result = predict_one(conn, m["id"], year)
            if result is None:
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO flv_crop_classification
                    (mun_id, year, predicted_crop, confidence, top_k_json,
                     model_version, features_json, predicted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    m["id"],
                    year,
                    result["predicted_crop"],
                    result["confidence"],
                    json.dumps(result["top_k"]),
                    MODEL_VERSION,
                    json.dumps(result["features"]),
                ),
            )
            count += 1
        except Exception as e:
            print(f"[FLV-CV] predict_all mun {m['id']}: {e}")
    conn.commit()
    print(f"[FLV-CV] {count} classificacoes CV persistidas (year={year}, model={MODEL_VERSION})")
    return count


def register():
    """Register the CV trainer. No-op in PR#4 (Pilar 4.A).

    The Pilar 3 retrain_controller currently exposes a single global trainer
    callback (`register_trainer(fn)` — see flv/model/retrain_controller.py),
    which the Pilar 2 ensemble already owns. Introducing a per-model-version
    registry is the explicit subject of PR#6 (Pilar 4.C — CV feedback loop).

    We return False here to signal "not wired yet" without clobbering the
    ensemble's callback. The pipeline calls this for forward compatibility.
    """
    return False


def run_all():
    """Pipeline entrypoint: train (if needed) + predict all muns for latest year."""
    from flv.db import get_conn
    conn = get_conn()
    t = train_and_persist(conn)
    if t.get("status") != "trained":
        print(f"[FLV-CV] Treino pulado: {t}")
        return 0
    print(f"[FLV-CV] Modelo treinado — samples={t['samples']} "
          f"acc={t['accuracy_in_sample']} f1={t['f1_macro_in_sample']}")
    return predict_all(conn)


def _now():
    import datetime as _dt
    return _dt.datetime.utcnow().isoformat(timespec="seconds")
