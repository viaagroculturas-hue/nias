"""FLV Sentinel STAC Collector — Scene metadata from Microsoft Planetary Computer.

Queries the public STAC API (no auth) for Sentinel-2 L2A, Sentinel-1 GRD and
Landsat C2 L2 scenes intersecting each tracked municipality. Persists scene
metadata (id, date, cloud cover, primary asset URL, bbox) to flv_sat_scenes.

Design:
  - NO raster download. We store scene metadata only; per-scene reads happen
    in flv/cv/feature_extractor.py on demand, so that this collector is fast,
    cache-friendly and works in CPU-only batch pipelines.
  - Best-effort: a failure on one platform or one municipality does not break
    the others. Empty result + printed warning is the graceful fallback.
  - Public / no secrets — same constraint as flv/collectors/macro.py.

Planetary Computer STAC endpoint:
  https://planetarycomputer.microsoft.com/api/stac/v1/search
"""
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta

STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1/search"

# Platforms to probe per municipality. The asset_key chooses which COG URL
# we persist (the "primary" band used downstream by the feature extractor).
PLATFORMS = [
    {
        "collection": "sentinel-2-l2a",
        "asset_key": "B08",           # NIR 10m for NDVI
        "max_cloud": 30.0,            # skip scenes cloudier than this
        "has_cloud_cover": True,
    },
    {
        "collection": "sentinel-1-grd",
        "asset_key": "vv",            # VV polarization (cloud-penetrating)
        "max_cloud": None,
        "has_cloud_cover": False,
    },
    {
        "collection": "landsat-c2-l2",
        "asset_key": "nir08",         # NIR band 5 for NDVI
        "max_cloud": 30.0,
        "has_cloud_cover": True,
    },
]

# Bounding box buffer (degrees) around the municipal centroid.
# ~0.15° ≈ 16 km at the equator — covers most municipalities.
BBOX_BUFFER_DEG = 0.15

# Days of history to fetch on each call (rolling window).
HISTORY_DAYS = 90


def fetch_all(limit_muns=None, history_days=HISTORY_DAYS):
    """Fetch scene metadata for all tracked municipalities.

    Args:
        limit_muns: Optional int — cap how many municipalities to hit this cycle.
                    Useful for cronjobs that want to spread work over days.
        history_days: How far back to look (default 90).

    Returns:
        int — total scenes inserted/updated.
    """
    from flv.db import get_conn
    conn = get_conn()
    _ensure_table(conn)

    sql = "SELECT id, ibge_code, name, lat, lon FROM flv_municipalities"
    if limit_muns:
        sql += f" LIMIT {int(limit_muns)}"
    muns = conn.execute(sql).fetchall()

    end = datetime.utcnow().date()
    start = end - timedelta(days=history_days)
    datetime_range = f"{start.isoformat()}T00:00:00Z/{end.isoformat()}T23:59:59Z"

    total = 0
    for mun in muns:
        bbox = _bbox_around(mun["lat"], mun["lon"])
        for platform in PLATFORMS:
            try:
                count = _fetch_one(conn, mun, platform, bbox, datetime_range)
                total += count
            except Exception as e:
                print(f"[FLV-Sentinel] {platform['collection']} mun {mun['name']} erro: {e}")

    conn.commit()
    print(f"[FLV-Sentinel] {total} cenas de satelite persistidas "
          f"({len(muns)} municipios x {len(PLATFORMS)} plataformas)")
    return total


def _fetch_one(conn, mun, platform, bbox, datetime_range, limit=25):
    """Query STAC for one (municipality, platform) and upsert scenes."""
    body = {
        "collections": [platform["collection"]],
        "bbox": bbox,
        "datetime": datetime_range,
        "limit": limit,
    }
    # Sort newest first so 'limit' gives the most recent scenes.
    body["sortby"] = [{"field": "properties.datetime", "direction": "desc"}]

    req = urllib.request.Request(
        STAC_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; nias-cv/1.0)",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # 429 = throttled; 503 = PC momentary overload. Retry silently next cycle.
        if e.code in (429, 503):
            return 0
        raise
    except urllib.error.URLError:
        return 0

    features = payload.get("features") or []
    count = 0
    for feat in features:
        parsed = _parse_feature(feat, platform)
        if parsed is None:
            continue
        scene_id, obs_date, cloud_pct, asset_url, bbox_feat = parsed
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO flv_sat_scenes
                    (mun_id, platform, scene_id, obs_date, cloud_pct, asset_url,
                     bbox_json, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mun["id"],
                    platform["collection"],
                    scene_id,
                    obs_date,
                    cloud_pct,
                    asset_url,
                    json.dumps(bbox_feat) if bbox_feat else None,
                    "planetary-computer",
                ),
            )
            count += 1
        except Exception:
            pass
    return count


def _parse_feature(feat, platform):
    """Extract (scene_id, date, cloud_pct, asset_url, bbox) from a STAC feature.

    Returns None if the feature is malformed or fails the cloud filter.
    """
    if not isinstance(feat, dict):
        return None
    scene_id = feat.get("id")
    props = feat.get("properties") or {}
    dt_str = props.get("datetime")
    if not scene_id or not dt_str:
        return None
    try:
        obs_date = dt_str[:10]  # YYYY-MM-DD
    except Exception:
        return None

    cloud_pct = None
    if platform["has_cloud_cover"]:
        raw = props.get("eo:cloud_cover")
        if raw is None:
            # Skip scenes without cloud info on optical platforms (rare but happens).
            return None
        try:
            cloud_pct = float(raw)
        except (TypeError, ValueError):
            return None
        if platform["max_cloud"] is not None and cloud_pct > platform["max_cloud"]:
            return None

    asset_url = None
    assets = feat.get("assets") or {}
    asset = assets.get(platform["asset_key"])
    if isinstance(asset, dict):
        asset_url = asset.get("href")

    bbox_feat = feat.get("bbox")
    return scene_id, obs_date, cloud_pct, asset_url, bbox_feat


def _bbox_around(lat, lon, buffer=BBOX_BUFFER_DEG):
    return [
        round(lon - buffer, 4),
        round(lat - buffer, 4),
        round(lon + buffer, 4),
        round(lat + buffer, 4),
    ]


def scenes_for_municipality(mun_id, platform=None, max_cloud=None, limit=30):
    """Helper used by feature_extractor: returns recent scene rows for one muni."""
    from flv.db import get_conn
    conn = get_conn()
    sql = ("SELECT platform, scene_id, obs_date, cloud_pct, asset_url, bbox_json "
           "FROM flv_sat_scenes WHERE mun_id = ?")
    args = [mun_id]
    if platform:
        sql += " AND platform = ?"
        args.append(platform)
    if max_cloud is not None:
        sql += " AND (cloud_pct IS NULL OR cloud_pct <= ?)"
        args.append(max_cloud)
    sql += " ORDER BY obs_date DESC LIMIT ?"
    args.append(limit)
    return conn.execute(sql, args).fetchall()


def _ensure_table(conn):
    """Idempotent table creation — used when the collector runs before init_db."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS flv_sat_scenes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id      INTEGER NOT NULL,
            platform    TEXT NOT NULL,
            scene_id    TEXT NOT NULL,
            obs_date    TEXT NOT NULL,
            cloud_pct   REAL,
            asset_url   TEXT,
            bbox_json   TEXT,
            source      TEXT DEFAULT 'planetary-computer',
            created_at  TEXT DEFAULT (datetime('now')),
            UNIQUE(mun_id, platform, scene_id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sat_scenes_mun_date "
        "ON flv_sat_scenes(mun_id, obs_date)"
    )
