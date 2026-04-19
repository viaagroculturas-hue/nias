"""FLV Retrain Controller — decides when to re-train forecasting models.

Reads rolling MAPE from `flv_accuracy`, compares against thresholds, and logs
the decision in `flv_model_runs`.

Triggers (OR semantics):
- `mape_30d > MAX_MAPE_PCT` (default 12%)
- `mape_30d > 1.3 * mape_30d_prior` (30% relative degradation vs the prior 30-day window)

Actual retraining is delegated to the model layer (Pilar 2 ensemble PR). This
module only *decides* and *records*. When the ensemble arrives, it will register
a callback via `register_trainer()`.
"""
from datetime import datetime, timedelta, timezone

MAX_MAPE_PCT = 12.0
RELATIVE_DEGRADATION = 1.30
MIN_SAMPLES = 5  # don't trigger on <5 evaluated predictions

_trainer_cb = None


def register_trainer(fn):
    """Register a callback fn(culture_slug, terminal, model_version) -> (ok, mape_after)."""
    global _trainer_cb
    _trainer_cb = fn


def _rolling_mape(conn, culture_slug, terminal, model_version, days, offset_days=0):
    """Rolling MAPE over [now-offset-days, now-offset]."""
    end = datetime.now(timezone.utc) - timedelta(days=offset_days)
    start = end - timedelta(days=days)
    sql = (
        "SELECT AVG(a.mape_pct) AS m, COUNT(a.id) AS n "
        "FROM flv_accuracy a "
        "JOIN flv_predictions p ON p.id = a.prediction_id "
        "JOIN flv_cultures c ON c.id = p.culture_id "
        "WHERE c.slug=? AND p.terminal=? AND p.model_version=? "
        "AND a.actual_date >= ? AND a.actual_date < ?"
    )
    row = conn.execute(
        sql,
        (
            culture_slug,
            terminal,
            model_version,
            start.strftime("%Y-%m-%d"),
            end.strftime("%Y-%m-%d"),
        ),
    ).fetchone()
    if not row or not row["n"]:
        return None, 0
    return float(row["m"]), int(row["n"])


def check_triggers(conn=None, max_mape=MAX_MAPE_PCT):
    """Inspect every (culture, terminal, model_version) combo and return the list
    of triggers. Each trigger is a dict with keys:
        culture_slug, terminal, model_version, mape_30d, mape_prior, reason
    """
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()

    combos = conn.execute(
        """
        SELECT c.slug AS culture_slug, p.terminal AS terminal, p.model_version AS model_version
        FROM flv_predictions p
        JOIN flv_cultures c ON c.id = p.culture_id
        GROUP BY c.slug, p.terminal, p.model_version
        """
    ).fetchall()

    triggers = []
    for c in combos:
        mape_now, n_now = _rolling_mape(
            conn, c["culture_slug"], c["terminal"], c["model_version"], days=30
        )
        if mape_now is None or n_now < MIN_SAMPLES:
            continue
        mape_prior, _ = _rolling_mape(
            conn,
            c["culture_slug"],
            c["terminal"],
            c["model_version"],
            days=30,
            offset_days=30,
        )

        reason = None
        if mape_now > max_mape:
            reason = f"mape_30d {mape_now:.2f}% > threshold {max_mape:.1f}%"
        elif mape_prior is not None and mape_prior > 0 and mape_now > RELATIVE_DEGRADATION * mape_prior:
            reason = (
                f"mape_30d {mape_now:.2f}% > {RELATIVE_DEGRADATION:.2f}x prior "
                f"({mape_prior:.2f}%)"
            )
        if reason:
            triggers.append(
                {
                    "culture_slug": c["culture_slug"],
                    "terminal": c["terminal"],
                    "model_version": c["model_version"],
                    "mape_30d": round(mape_now, 4),
                    "mape_prior": round(mape_prior, 4) if mape_prior is not None else None,
                    "reason": reason,
                }
            )
    return triggers


def _log_run(conn, trigger, status, mape_after=None, notes=None):
    conn.execute(
        """
        INSERT INTO flv_model_runs
        (culture_slug, terminal, model_version, started_at, finished_at,
         mape_before, mape_after, trigger_reason, status, notes)
        VALUES (?,?,?,datetime('now'),datetime('now'),?,?,?,?,?)
        """,
        (
            trigger["culture_slug"],
            trigger["terminal"],
            trigger["model_version"],
            trigger["mape_30d"],
            mape_after,
            trigger["reason"],
            status,
            notes,
        ),
    )
    conn.commit()


def run(conn=None, dry_run=False):
    """Main entrypoint invoked by the pipeline. Returns dict with triggers + actions taken."""
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()

    triggers = check_triggers(conn)
    actions = []
    for t in triggers:
        if dry_run or _trainer_cb is None:
            _log_run(conn, t, status="deferred", notes="no trainer registered" if not dry_run else "dry_run")
            actions.append({"trigger": t, "status": "deferred"})
            continue
        try:
            ok, mape_after = _trainer_cb(t["culture_slug"], t["terminal"], t["model_version"])
            status = "completed" if ok else "failed"
            _log_run(conn, t, status=status, mape_after=mape_after)
            actions.append({"trigger": t, "status": status, "mape_after": mape_after})
        except Exception as e:
            _log_run(conn, t, status="failed", notes=str(e)[:240])
            actions.append({"trigger": t, "status": "failed", "error": str(e)})
    return {"triggers": triggers, "actions": actions}
