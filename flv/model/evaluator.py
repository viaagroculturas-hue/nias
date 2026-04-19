"""FLV Prediction Evaluator — compares past predictions to observed prices.

For every row in `flv_predictions` with `target_date <= today` that does not yet
have an entry in `flv_accuracy`, we:

1. Look up the actual observed price in `flv_ceasa_prices` on `target_date` (or
   the nearest earlier date within a 3-day window, since terminals skip
   weekends/holidays).
2. Compute MAPE = |predicted - actual| / actual * 100 (guard against
   divide-by-zero).
3. Insert into `flv_accuracy(prediction_id, actual_price, actual_date,
   mape_pct, evaluated_at)`.

Also exposes `rolling_mape(culture_slug, terminal, window_days, model_version)`
and `summary()` for the `/api/flv/model/health` route.
"""
from datetime import datetime, timedelta, timezone

# Lookback window when the exact target_date has no price (weekends/holidays).
MAX_PRICE_LOOKBACK_DAYS = 3


def _today_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _find_actual_price(conn, culture_id, terminal, target_date):
    """Return (actual_price, actual_date) or (None, None) if unavailable.

    Tries the exact `target_date` first, then walks backwards up to
    MAX_PRICE_LOOKBACK_DAYS days.
    """
    sql_exact = (
        "SELECT price_date, price_avg FROM flv_ceasa_prices "
        "WHERE culture_id=? AND terminal=? AND price_date=?"
    )
    row = conn.execute(sql_exact, (culture_id, terminal, target_date)).fetchone()
    if row and row["price_avg"] is not None and row["price_avg"] > 0:
        return row["price_avg"], row["price_date"]

    # Closest earlier price within lookback window.
    min_date = (
        datetime.strptime(target_date, "%Y-%m-%d") - timedelta(days=MAX_PRICE_LOOKBACK_DAYS)
    ).strftime("%Y-%m-%d")
    sql_near = (
        "SELECT price_date, price_avg FROM flv_ceasa_prices "
        "WHERE culture_id=? AND terminal=? AND price_date<=? AND price_date>=? "
        "ORDER BY price_date DESC LIMIT 1"
    )
    row = conn.execute(sql_near, (culture_id, terminal, target_date, min_date)).fetchone()
    if row and row["price_avg"] is not None and row["price_avg"] > 0:
        return row["price_avg"], row["price_date"]

    # Fallback: ignore terminal (some terminals share price feeds).
    sql_any = (
        "SELECT price_date, price_avg FROM flv_ceasa_prices "
        "WHERE culture_id=? AND price_date=? AND price_avg IS NOT NULL AND price_avg>0 "
        "ORDER BY price_avg LIMIT 1"
    )
    row = conn.execute(sql_any, (culture_id, target_date)).fetchone()
    if row:
        return row["price_avg"], row["price_date"]
    return None, None


def evaluate_predictions(conn=None, max_rows=10000):
    """Evaluate pending predictions. Returns count_evaluated."""
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()

    today = _today_iso()
    sql = (
        "SELECT p.id, p.culture_id, p.terminal, p.target_date, p.predicted_price, p.model_version "
        "FROM flv_predictions p "
        "LEFT JOIN flv_accuracy a ON a.prediction_id = p.id "
        "WHERE p.target_date <= ? AND a.id IS NULL "
        "ORDER BY p.target_date ASC LIMIT ?"
    )
    rows = conn.execute(sql, (today, max_rows)).fetchall()
    count = 0
    for r in rows:
        actual, actual_date = _find_actual_price(
            conn, r["culture_id"], r["terminal"], r["target_date"]
        )
        if actual is None or actual <= 0:
            continue
        predicted = r["predicted_price"]
        if predicted is None:
            continue
        mape = abs(predicted - actual) / actual * 100.0
        conn.execute(
            "INSERT INTO flv_accuracy (prediction_id, actual_price, actual_date, mape_pct) "
            "VALUES (?,?,?,?)",
            (r["id"], float(actual), actual_date, round(mape, 4)),
        )
        count += 1
    conn.commit()
    return count


def rolling_mape(conn, culture_slug=None, terminal=None, window_days=30, model_version=None):
    """Compute mean MAPE over last `window_days` for the matching filter.

    Returns (mape_pct, n) where n is the sample size. Returns (None, 0) when empty.
    """
    since = (
        datetime.now(timezone.utc) - timedelta(days=window_days)
    ).strftime("%Y-%m-%d")

    sql = (
        "SELECT AVG(a.mape_pct) AS m, COUNT(a.id) AS n "
        "FROM flv_accuracy a "
        "JOIN flv_predictions p ON p.id = a.prediction_id "
        "JOIN flv_cultures c ON c.id = p.culture_id "
        "WHERE a.actual_date >= ?"
    )
    args = [since]
    if culture_slug:
        sql += " AND c.slug = ?"
        args.append(culture_slug)
    if terminal:
        sql += " AND p.terminal = ?"
        args.append(terminal)
    if model_version:
        sql += " AND p.model_version = ?"
        args.append(model_version)

    row = conn.execute(sql, args).fetchone()
    if not row or not row["n"]:
        return None, 0
    return round(row["m"], 4), row["n"]


def summary(conn=None):
    """Return MLOps health summary for /api/flv/model/health."""
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()

    # List every (culture, terminal, model_version) combo seen in predictions.
    combos = conn.execute(
        """
        SELECT c.slug AS culture, p.terminal AS terminal, p.model_version AS model_version,
               MAX(p.generated_at) AS last_generated
        FROM flv_predictions p
        JOIN flv_cultures c ON c.id = p.culture_id
        GROUP BY c.slug, p.terminal, p.model_version
        ORDER BY c.slug, p.terminal, p.model_version
        """
    ).fetchall()

    out = []
    for c in combos:
        m7, n7 = rolling_mape(conn, c["culture"], c["terminal"], 7, c["model_version"])
        m30, n30 = rolling_mape(conn, c["culture"], c["terminal"], 30, c["model_version"])
        last_eval = conn.execute(
            """
            SELECT MAX(a.evaluated_at) AS last_evaluated
            FROM flv_accuracy a
            JOIN flv_predictions p ON p.id = a.prediction_id
            JOIN flv_cultures cc ON cc.id = p.culture_id
            WHERE cc.slug=? AND p.terminal=? AND p.model_version=?
            """,
            (c["culture"], c["terminal"], c["model_version"]),
        ).fetchone()
        last_retrain = conn.execute(
            """
            SELECT MAX(finished_at) AS last_retrain
            FROM flv_model_runs
            WHERE culture_slug=? AND terminal=? AND status='completed'
            """,
            (c["culture"], c["terminal"]),
        ).fetchone()
        out.append(
            {
                "culture": c["culture"],
                "terminal": c["terminal"],
                "model_version": c["model_version"],
                "mape_7d": m7,
                "mape_7d_n": n7,
                "mape_30d": m30,
                "mape_30d_n": n30,
                "last_prediction_at": c["last_generated"],
                "last_evaluated_at": last_eval["last_evaluated"] if last_eval else None,
                "last_retrain_at": last_retrain["last_retrain"] if last_retrain else None,
            }
        )
    return out
