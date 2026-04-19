"""FLV CV Feature Extractor — builds one feature vector per (municipality, year).

Combines signals that are ALREADY in the database, so extraction runs in pure
Python+SQL without GDAL/rasterio:

  * flv_ndvi      — mean / max / std / slope of NDVI over the target year
  * flv_climate   — mean temp, precip total, heat-stress days
  * flv_sat_scenes — counts of Sentinel-2 / Sentinel-1 / Landsat scenes and
                     mean cloud cover (proxy for observability)
  * flv_lulc_stats — prior-year area fractions per crop class (strong prior)
  * flv_macro     — mean USD/BRL and IPCA over the year (context)
  * flv_cultures  — static lat/state features via municipal metadata

The resulting feature vector is stable in ORDER — see FEATURE_NAMES — so
the classifier persists a single ordered list.
"""
import math
import statistics

# NOTE: FEATURE_NAMES is the canonical order. Any change here REQUIRES a
# model-version bump in crop_classifier.py (rf-cv-v1 → rf-cv-v2).
FEATURE_NAMES = [
    # geography
    "lat",
    "lon",
    "abs_lat",
    # NDVI (year-aggregated)
    "ndvi_mean",
    "ndvi_max",
    "ndvi_min",
    "ndvi_std",
    "ndvi_slope",
    "ndvi_count",
    # climate
    "temp_mean",
    "temp_max",
    "precip_total",
    "heat_stress_days",
    "climate_count",
    # satellite observability
    "s2_scenes",
    "s1_scenes",
    "landsat_scenes",
    "cloud_mean",
    # LULC priors (stable subset)
    "lulc_soja_pct",
    "lulc_milho_pct",
    "lulc_cana_pct",
    "lulc_pastagem_pct",
    "lulc_floresta_pct",
    "lulc_tomate_pct",
    "lulc_banana_pct",
    "lulc_laranja_pct",
    # macro
    "usd_mean",
    "ipca_mean",
]

LULC_PRIORS = [
    "soja", "milho", "cana", "pastagem", "floresta",
    "tomate", "banana", "laranja",
]


def extract(conn, mun_id, year):
    """Build a feature vector for one (mun_id, year). Missing signals → 0.0."""
    feats = {n: 0.0 for n in FEATURE_NAMES}
    mun = conn.execute(
        "SELECT id, lat, lon, state_uf FROM flv_municipalities WHERE id = ?",
        (mun_id,),
    ).fetchone()
    if not mun:
        return feats
    feats["lat"] = mun["lat"] or 0.0
    feats["lon"] = mun["lon"] or 0.0
    feats["abs_lat"] = abs(mun["lat"] or 0.0)

    _fill_ndvi(conn, mun_id, year, feats)
    _fill_climate(conn, mun_id, year, feats)
    _fill_sat_scenes(conn, mun_id, year, feats)
    _fill_lulc(conn, mun_id, year, feats)
    _fill_macro(conn, year, feats)
    return feats


def extract_vector(conn, mun_id, year):
    """Return a plain list aligned with FEATURE_NAMES (for scikit-learn)."""
    feats = extract(conn, mun_id, year)
    return [feats[n] for n in FEATURE_NAMES]


def _fill_ndvi(conn, mun_id, year, feats):
    rows = conn.execute(
        """
        SELECT ndvi_value, obs_date FROM flv_ndvi
        WHERE mun_id = ? AND obs_date LIKE ?
        ORDER BY obs_date
        """,
        (mun_id, f"{year}%"),
    ).fetchall()
    if not rows:
        return
    values = [r["ndvi_value"] for r in rows if r["ndvi_value"] is not None]
    if not values:
        return
    feats["ndvi_mean"] = sum(values) / len(values)
    feats["ndvi_max"] = max(values)
    feats["ndvi_min"] = min(values)
    feats["ndvi_std"] = statistics.pstdev(values) if len(values) > 1 else 0.0
    feats["ndvi_count"] = float(len(values))
    # Simple slope: first-half mean vs second-half mean over the window.
    half = len(values) // 2
    if half >= 2:
        left = sum(values[:half]) / half
        right = sum(values[half:]) / (len(values) - half)
        feats["ndvi_slope"] = right - left


def _fill_climate(conn, mun_id, year, feats):
    rows = conn.execute(
        """
        SELECT temp_max_c, temp_min_c, precip_mm
        FROM flv_climate
        WHERE mun_id = ? AND obs_date LIKE ?
        """,
        (mun_id, f"{year}%"),
    ).fetchall()
    if not rows:
        return
    temps = []
    maxes = []
    precip_total = 0.0
    heat_stress = 0
    for r in rows:
        tmax = r["temp_max_c"]
        tmin = r["temp_min_c"]
        p = r["precip_mm"] or 0.0
        precip_total += p
        if tmax is not None and tmin is not None:
            temps.append((tmax + tmin) / 2.0)
            maxes.append(tmax)
            if tmax >= 35.0:
                heat_stress += 1
    if temps:
        feats["temp_mean"] = sum(temps) / len(temps)
        feats["temp_max"] = max(maxes)
    feats["precip_total"] = precip_total
    feats["heat_stress_days"] = float(heat_stress)
    feats["climate_count"] = float(len(rows))


def _fill_sat_scenes(conn, mun_id, year, feats):
    rows = conn.execute(
        """
        SELECT platform, cloud_pct FROM flv_sat_scenes
        WHERE mun_id = ? AND obs_date LIKE ?
        """,
        (mun_id, f"{year}%"),
    ).fetchall()
    if not rows:
        return
    clouds = []
    for r in rows:
        platform = r["platform"]
        if platform == "sentinel-2-l2a":
            feats["s2_scenes"] += 1.0
        elif platform == "sentinel-1-grd":
            feats["s1_scenes"] += 1.0
        elif platform == "landsat-c2-l2":
            feats["landsat_scenes"] += 1.0
        if r["cloud_pct"] is not None:
            clouds.append(r["cloud_pct"])
    if clouds:
        feats["cloud_mean"] = sum(clouds) / len(clouds)


def _fill_lulc(conn, mun_id, year, feats):
    # Prefer the target year; fall back to the most recent prior year we have.
    rows = conn.execute(
        """
        SELECT crop_class, area_pct FROM flv_lulc_stats
        WHERE mun_id = ? AND year = ?
        """,
        (mun_id, year),
    ).fetchall()
    if not rows:
        rows = conn.execute(
            """
            SELECT crop_class, area_pct FROM flv_lulc_stats
            WHERE mun_id = ? AND year < ?
            ORDER BY year DESC
            """,
            (mun_id, year),
        ).fetchall()
    if not rows:
        return
    seen = {}
    for r in rows:
        cls = r["crop_class"]
        if cls in seen:
            continue
        seen[cls] = r["area_pct"] or 0.0
    for slug in LULC_PRIORS:
        feats[f"lulc_{slug}_pct"] = seen.get(slug, 0.0)


def _fill_macro(conn, year, feats):
    row = conn.execute(
        """
        SELECT series, AVG(value) AS v
        FROM flv_macro
        WHERE obs_date LIKE ?
        GROUP BY series
        """,
        (f"{year}%",),
    ).fetchall()
    for r in row:
        if r["series"] == "usd_brl":
            feats["usd_mean"] = r["v"] or 0.0
        elif r["series"] == "ipca_yoy":
            feats["ipca_mean"] = r["v"] or 0.0


def label_for(conn, mun_id, year):
    """Weak label: dominant crop_class in flv_lulc_stats for the year.

    Returns a crop slug (string) or None if no LULC rows exist.
    """
    row = conn.execute(
        """
        SELECT crop_class, area_pct FROM flv_lulc_stats
        WHERE mun_id = ? AND year = ?
        ORDER BY area_pct DESC
        LIMIT 1
        """,
        (mun_id, year),
    ).fetchone()
    if not row:
        row = conn.execute(
            """
            SELECT crop_class, area_pct FROM flv_lulc_stats
            WHERE mun_id = ? AND year < ?
            ORDER BY year DESC, area_pct DESC
            LIMIT 1
            """,
            (mun_id, year),
        ).fetchone()
    if not row:
        return None
    return row["crop_class"]


def dataset(conn, years=None, min_samples_per_class=2):
    """Assemble (X, y, meta) for training. Filters out rare classes (<min)."""
    if years is None:
        row = conn.execute(
            "SELECT DISTINCT year FROM flv_lulc_stats ORDER BY year DESC"
        ).fetchall()
        years = [r["year"] for r in row] or []

    rows_X = []
    rows_y = []
    rows_meta = []
    muns = conn.execute("SELECT id FROM flv_municipalities").fetchall()
    for m in muns:
        for y in years:
            lbl = label_for(conn, m["id"], y)
            if not lbl:
                continue
            vec = extract_vector(conn, m["id"], y)
            if not any(abs(v) > 1e-9 for v in vec[3:]):  # skip empty rows
                continue
            rows_X.append(vec)
            rows_y.append(lbl)
            rows_meta.append({"mun_id": m["id"], "year": y})

    # Drop classes with too few samples (would break stratified metrics).
    counts = {}
    for lbl in rows_y:
        counts[lbl] = counts.get(lbl, 0) + 1
    keep = {lbl for lbl, c in counts.items() if c >= min_samples_per_class}
    X, y, meta = [], [], []
    for xv, yv, mv in zip(rows_X, rows_y, rows_meta):
        if yv in keep:
            X.append(xv)
            y.append(yv)
            meta.append(mv)
    return X, y, meta
