"""FLV CV Change Detection — Pilar 4.B.

Compares recent signals against a 12-month baseline to flag anomalies that
plausibly indicate a shift in land-use or crop health. The detectors are
deliberately cheap (pure SQL aggregation + Python thresholds) so they can
run every pipeline cycle on the existing SQLite database, without any
raster reads.

Kinds of anomalies emitted:

  * ``ndvi_drop``        — NDVI fell ≥ NDVI_DROP_THRESHOLD below the 12-month
                            mean over a 30-day window (possible early-stress
                            or harvest).
  * ``bare_soil_off_season`` — mean NDVI < BARE_SOIL_NDVI outside the
                            expected off-season window for that latitude
                            (possible soil conversion or double-cropping).
  * ``lulc_shift``       — LULC dominant class changed year-over-year by
                            ≥ LULC_SHIFT_THRESHOLD area_pct (possible land
                            conversion, e.g. pasture → soy).
  * ``pivot_new``        — step-function increase in S2 observability AND
                            NDVI mean year-over-year (heuristic for new
                            pivot irrigation).

All severity thresholds are tuneable constants at the top of the module.
"""
from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone

# -- Thresholds (tuneable) --------------------------------------------------
NDVI_DROP_THRESHOLD = 0.18          # alert when current NDVI < baseline - 0.18
NDVI_DROP_WARN = 0.10
BARE_SOIL_NDVI = 0.22               # below this in growing season → alert
LULC_SHIFT_THRESHOLD = 0.15         # 15 percentage-point swing in dominant class
PIVOT_NDVI_JUMP = 0.12

BASELINE_WINDOW_DAYS = 365
RECENT_WINDOW_DAYS = 30


def run_all(conn=None, limit_muns: int = None) -> int:
    """Run every detector on every municipality. Returns total anomalies upserted."""
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()

    sql = "SELECT id, name, state_uf, lat FROM flv_municipalities ORDER BY id"
    if limit_muns:
        sql += f" LIMIT {int(limit_muns)}"
    muns = conn.execute(sql).fetchall()

    total = 0
    for m in muns:
        total += _run_for_mun(conn, m)
    conn.commit()
    print(f"[FLV-CV-ChangeDetect] {total} anomalias persistidas ({len(muns)} municipios)")
    return total


def _run_for_mun(conn, mun) -> int:
    n = 0
    ndvi_anoms = detect_ndvi_anomalies(conn, mun)
    lulc_anoms = detect_lulc_shift(conn, mun)
    pivot_anoms = detect_pivot_new(conn, mun)
    for a in ndvi_anoms + lulc_anoms + pivot_anoms:
        _upsert(conn, a)
        n += 1
    return n


# ---------------------------------------------------------------------------
# NDVI-based detectors
# ---------------------------------------------------------------------------
def detect_ndvi_anomalies(conn, mun) -> list:
    """Compare last 30d NDVI mean against the 12-month baseline."""
    now = datetime.now(timezone.utc).date()
    recent_start = now - timedelta(days=RECENT_WINDOW_DAYS)
    baseline_start = now - timedelta(days=BASELINE_WINDOW_DAYS)

    rows = conn.execute(
        """
        SELECT ndvi_value, obs_date FROM flv_ndvi
        WHERE mun_id = ? AND obs_date >= ?
        ORDER BY obs_date
        """,
        (mun["id"], baseline_start.isoformat()),
    ).fetchall()
    if len(rows) < 3:
        return []

    recent, baseline = [], []
    latest_date = None
    for r in rows:
        try:
            d = datetime.strptime(r["obs_date"][:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        v = r["ndvi_value"]
        if v is None:
            continue
        if d >= recent_start:
            recent.append(v)
            latest_date = max(latest_date or d, d)
        else:
            baseline.append(v)

    if len(recent) < 1 or len(baseline) < 2:
        return []

    baseline_mean = sum(baseline) / len(baseline)
    current = sum(recent) / len(recent)
    delta = current - baseline_mean

    results = []
    # 1) NDVI drop (severity tiers)
    if delta <= -NDVI_DROP_THRESHOLD:
        severity = "alert"
    elif delta <= -NDVI_DROP_WARN:
        severity = "warn"
    else:
        severity = None
    if severity:
        results.append({
            "mun_id": mun["id"],
            "detected_at": (latest_date or now).isoformat(),
            "kind": "ndvi_drop",
            "severity": severity,
            "delta": round(delta, 4),
            "baseline_value": round(baseline_mean, 4),
            "current_value": round(current, 4),
            "details_json": json.dumps({
                "recent_n": len(recent),
                "baseline_n": len(baseline),
                "window_days": RECENT_WINDOW_DAYS,
            }),
        })

    # 2) Bare-soil off-season (latitude-aware)
    if current < BARE_SOIL_NDVI and _is_growing_season(mun["lat"], latest_date or now):
        results.append({
            "mun_id": mun["id"],
            "detected_at": (latest_date or now).isoformat(),
            "kind": "bare_soil_off_season",
            "severity": "warn",
            "delta": round(current - BARE_SOIL_NDVI, 4),
            "baseline_value": BARE_SOIL_NDVI,
            "current_value": round(current, 4),
            "details_json": json.dumps({"lat": mun["lat"]}),
        })
    return results


def _is_growing_season(lat: float, d: "datetime.date") -> bool:
    """Rough growing-season mask by hemisphere.

    Southern hemisphere (lat < 0): growing season Oct..Apr.
    Northern hemisphere (lat ≥ 0): Apr..Oct.
    Equatorial belt (|lat| < 10): treat as always-growing.
    """
    if lat is None or abs(lat) < 10:
        return True
    if lat < 0:
        return d.month >= 10 or d.month <= 4
    return 4 <= d.month <= 10


# ---------------------------------------------------------------------------
# LULC shift detector
# ---------------------------------------------------------------------------
def detect_lulc_shift(conn, mun) -> list:
    """Detect a dominant-class change year-over-year in flv_lulc_stats."""
    rows = conn.execute(
        """
        SELECT year, crop_class, area_pct
        FROM flv_lulc_stats
        WHERE mun_id = ?
        ORDER BY year DESC, area_pct DESC
        """,
        (mun["id"],),
    ).fetchall()
    if not rows:
        return []

    by_year: dict = {}
    for r in rows:
        by_year.setdefault(r["year"], []).append(r)

    years = sorted(by_year.keys(), reverse=True)
    if len(years) < 2:
        return []
    current_year, prior_year = years[0], years[1]
    curr_top = by_year[current_year][0]
    prior_top = by_year[prior_year][0]
    if curr_top["crop_class"] == prior_top["crop_class"]:
        return []

    # Measure the year-over-year growth of the NEW dominant crop itself.
    # Prior-year area_pct of the current dominant class (default 0 if absent).
    prior_same = 0.0
    for r in by_year[prior_year]:
        if r["crop_class"] == curr_top["crop_class"]:
            prior_same = float(r["area_pct"] or 0.0)
            break
    delta = float(curr_top["area_pct"]) - prior_same
    if delta < LULC_SHIFT_THRESHOLD:
        return []

    return [{
        "mun_id": mun["id"],
        "detected_at": f"{current_year}-12-31",
        "kind": "lulc_shift",
        "severity": "warn" if delta < 0.3 else "alert",
        "delta": round(delta, 4),
        "baseline_value": round(prior_same, 4),
        "current_value": float(curr_top["area_pct"]),
        "details_json": json.dumps({
            "prior_year": prior_year,
            "prior_dominant": prior_top["crop_class"],
            "current_dominant": curr_top["crop_class"],
            "prior_dominant_area_pct": float(prior_top["area_pct"]),
        }),
    }]


# ---------------------------------------------------------------------------
# Pivot-new heuristic
# ---------------------------------------------------------------------------
def detect_pivot_new(conn, mun) -> list:
    """Flag munis where S2 observability AND NDVI mean jumped vs. prior year.

    Rough proxy for a new irrigated pivot coming online. Relies on STAC scene
    counts from flv_sat_scenes plus NDVI mean from flv_ndvi.
    """
    now_year = datetime.now(timezone.utc).year
    prior_year = now_year - 1

    s2_now = _count_scenes(conn, mun["id"], "sentinel-2-l2a", now_year)
    s2_prior = _count_scenes(conn, mun["id"], "sentinel-2-l2a", prior_year)
    ndvi_now = _ndvi_mean(conn, mun["id"], now_year)
    ndvi_prior = _ndvi_mean(conn, mun["id"], prior_year)
    if s2_now is None or s2_prior is None or ndvi_now is None or ndvi_prior is None:
        return []
    # Need a real prior of meaningful size to compare against.
    if s2_prior < 3 or ndvi_prior == 0:
        return []

    scenes_ratio = s2_now / max(1, s2_prior)
    ndvi_jump = ndvi_now - ndvi_prior
    if scenes_ratio >= 1.5 and ndvi_jump >= PIVOT_NDVI_JUMP:
        return [{
            "mun_id": mun["id"],
            "detected_at": f"{now_year}-12-31",
            "kind": "pivot_new",
            "severity": "info",
            "delta": round(ndvi_jump, 4),
            "baseline_value": round(ndvi_prior, 4),
            "current_value": round(ndvi_now, 4),
            "details_json": json.dumps({
                "s2_scenes_now": s2_now,
                "s2_scenes_prior": s2_prior,
            }),
        }]
    return []


def _count_scenes(conn, mun_id, platform, year) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS n FROM flv_sat_scenes
        WHERE mun_id = ? AND platform = ? AND obs_date LIKE ?
        """,
        (mun_id, platform, f"{year}%"),
    ).fetchone()
    return int(row["n"]) if row else 0


def _ndvi_mean(conn, mun_id, year):
    row = conn.execute(
        "SELECT AVG(ndvi_value) AS m FROM flv_ndvi WHERE mun_id = ? AND obs_date LIKE ?",
        (mun_id, f"{year}%"),
    ).fetchone()
    return float(row["m"]) if row and row["m"] is not None else None


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def _upsert(conn, anomaly: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO flv_cv_anomalies
        (mun_id, detected_at, kind, severity, delta, baseline_value, current_value, details_json, created_at)
        VALUES (?,?,?,?,?,?,?,?, datetime('now'))
        """,
        (
            anomaly["mun_id"],
            anomaly["detected_at"],
            anomaly["kind"],
            anomaly["severity"],
            anomaly.get("delta"),
            anomaly.get("baseline_value"),
            anomaly.get("current_value"),
            anomaly.get("details_json"),
        ),
    )


def recent(conn=None, since: str = None, limit: int = 200) -> list:
    """Return anomalies with detected_at >= since (ISO date)."""
    if conn is None:
        from flv.db import get_conn
        conn = get_conn()
    args: list = []
    sql = (
        "SELECT a.mun_id, m.name AS mun_name, m.state_uf, m.ibge_code, "
        "a.detected_at, a.kind, a.severity, a.delta, a.baseline_value, "
        "a.current_value, a.details_json "
        "FROM flv_cv_anomalies a "
        "JOIN flv_municipalities m ON m.id = a.mun_id "
    )
    where = []
    if since:
        where.append("a.detected_at >= ?")
        args.append(since)
    if where:
        sql += "WHERE " + " AND ".join(where) + " "
    sql += "ORDER BY a.detected_at DESC, a.id DESC LIMIT ?"
    args.append(int(limit))
    rows = conn.execute(sql, args).fetchall()
    return [dict(r) for r in rows]
