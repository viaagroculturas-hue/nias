"""Bio Intelligence core for Sentinel-2 NDVI and hortifruti detection.

The module is intentionally dependency-light: callers may pass Python
sequences or NumPy arrays when NumPy is available.  It computes current NDVI,
compares it with historical baselines, detects spectral signatures compatible
with intensive fruit and vegetable production, and emits supply-risk alerts
when a production pole falls 15% below its NDVI mean.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import math
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:  # NumPy is optional in the base app, but supported when present.
    import numpy as _np
except Exception:  # pragma: no cover - exercised in minimal environments.
    _np = None


BandInput = Any
Pixel = Tuple[int, int]

SUPPLY_RISK_DROP_PCT = 15.0
NDVI_EPSILON = 1e-9


@dataclass(frozen=True)
class NDVIComparison:
    """NDVI state for one production pole."""

    pole_id: str
    current_ndvi: float
    historical_mean: float
    historical_std: float
    delta: float
    delta_pct: float
    obs_date: Optional[str] = None
    sample_size: int = 0

    @property
    def risk_triggered(self) -> bool:
        """Whether current NDVI is at least 15% below the historical mean."""

        return self.delta_pct <= -(SUPPLY_RISK_DROP_PCT - 1e-9)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "pole_id": self.pole_id,
            "current_ndvi": round(self.current_ndvi, 4),
            "historical_mean": round(self.historical_mean, 4),
            "historical_std": round(self.historical_std, 4),
            "delta": round(self.delta, 4),
            "delta_pct": round(self.delta_pct, 2),
            "obs_date": self.obs_date,
            "sample_size": self.sample_size,
            "risk_triggered": self.risk_triggered,
        }


@dataclass(frozen=True)
class SpectralSignatureDetection:
    """Detected spectral signature compatible with hortifruti production."""

    crop_type: str
    confidence: float
    centroid: Pixel
    pixel_count: int
    ndvi_mean: float
    ndvi_std: float
    ndvi_texture: float
    red_edge_mean: Optional[float] = None
    source: str = "sentinel-2"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        payload = {
            "crop_type": self.crop_type,
            "confidence": round(self.confidence, 4),
            "centroid": {"row": self.centroid[0], "col": self.centroid[1]},
            "pixel_count": self.pixel_count,
            "ndvi_mean": round(self.ndvi_mean, 4),
            "ndvi_std": round(self.ndvi_std, 4),
            "ndvi_texture": round(self.ndvi_texture, 4),
            "source": self.source,
            "metadata": self.metadata,
        }
        if self.red_edge_mean is not None:
            payload["red_edge_mean"] = round(self.red_edge_mean, 4)
        return payload


def calculate_ndvi(nir: BandInput, red: BandInput) -> BandInput:
    """Calculate Sentinel-2 NDVI from B08 (NIR) and B04 (red) bands.

    Returns a NumPy array when NumPy is available and the input is array-like;
    otherwise returns nested Python lists preserving the raster shape.
    """

    if _np is not None:
        nir_arr = _np.asarray(nir, dtype=float)
        red_arr = _np.asarray(red, dtype=float)
        denominator = nir_arr + red_arr
        return _np.divide(
            nir_arr - red_arr,
            denominator,
            out=_np.zeros_like(nir_arr, dtype=float),
            where=_np.abs(denominator) > NDVI_EPSILON,
        )

    nir_matrix = _to_matrix(nir)
    red_matrix = _to_matrix(red)
    _validate_same_shape(nir_matrix, red_matrix)
    ndvi = []
    for row_idx, nir_row in enumerate(nir_matrix):
        ndvi_row = []
        for col_idx, nir_value in enumerate(nir_row):
            red_value = red_matrix[row_idx][col_idx]
            denominator = nir_value + red_value
            ndvi_row.append(0.0 if abs(denominator) <= NDVI_EPSILON else (nir_value - red_value) / denominator)
        ndvi.append(ndvi_row)
    return ndvi


def compare_ndvi_current_vs_historical(
    pole_id: str,
    current_ndvi: Any,
    historical_ndvi: Iterable[Any],
    obs_date: Optional[str] = None,
) -> NDVIComparison:
    """Compare current NDVI with historical values for one production pole."""

    current = _mean_numeric(current_ndvi)
    history = [_mean_numeric(item) for item in historical_ndvi]
    history = [value for value in history if value is not None and math.isfinite(value)]
    if current is None or not math.isfinite(current):
        raise ValueError("current_ndvi must contain at least one finite value")
    if not history:
        raise ValueError("historical_ndvi must contain at least one finite value")

    baseline = mean(history)
    delta = current - baseline
    delta_pct = 0.0 if abs(baseline) <= NDVI_EPSILON else (delta / baseline) * 100.0
    return NDVIComparison(
        pole_id=pole_id,
        current_ndvi=current,
        historical_mean=baseline,
        historical_std=pstdev(history) if len(history) > 1 else 0.0,
        delta=delta,
        delta_pct=delta_pct,
        obs_date=obs_date,
        sample_size=len(history),
    )


def generate_supply_risk_alert(
    comparison: NDVIComparison,
    *,
    culture_slug: Optional[str] = None,
    municipality: Optional[str] = None,
    valid_hours: int = 72,
) -> Optional[Dict[str, Any]]:
    """Generate a 'Risco de Oferta' alert if NDVI is 15% below baseline."""

    if not comparison.risk_triggered:
        return None

    location = municipality or comparison.pole_id
    product = culture_slug or "hortifruti"
    now = datetime.now(timezone.utc)
    return {
        "type": "Risco de Oferta",
        "alert_type": "risco_oferta",
        "severity": "laranja" if comparison.delta_pct > -25 else "vermelho",
        "region_key": comparison.pole_id,
        "culture_slug": culture_slug,
        "municipality": municipality,
        "trigger_value": round(comparison.current_ndvi, 4),
        "threshold_value": round(comparison.historical_mean * (1 - SUPPLY_RISK_DROP_PCT / 100.0), 4),
        "impact_supply_pct": round(comparison.delta_pct, 2),
        "impact_price_pct": round(min(80.0, abs(comparison.delta_pct) * 1.6), 2),
        "message": (
            f"Risco de Oferta em {location}: NDVI atual de {product} "
            f"({comparison.current_ndvi:.3f}) está {abs(comparison.delta_pct):.1f}% "
            f"abaixo da média histórica ({comparison.historical_mean:.3f})."
        ),
        "obs_date": comparison.obs_date,
        "valid_until": (now + timedelta(hours=valid_hours)).strftime("%Y-%m-%d %H:%M:%S"),
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
    }


def recognize_spectral_signature(
    sentinel2_bands: Mapping[str, BandInput],
    *,
    min_pixels: int = 12,
    min_confidence: float = 0.62,
) -> List[SpectralSignatureDetection]:
    """Identify new hortifruti production points from Sentinel-2 bands.

    Expected bands are Sentinel-2 B04 (red) and B08 (NIR).  Optional B03
    (green), B11 (SWIR) and B05/B06/B07 (red-edge) refine confidence.
    The detector searches contiguous patches with high vegetation vigor,
    red-edge response and irrigation-compatible moisture profile.
    """

    red = _get_band(sentinel2_bands, "B04", "red")
    nir = _get_band(sentinel2_bands, "B08", "nir", "NIR")
    green = _get_optional_band(sentinel2_bands, "B03", "green")
    swir = _get_optional_band(sentinel2_bands, "B11", "swir", "SWIR")
    red_edge = _get_optional_band(sentinel2_bands, "B05", "B06", "B07", "red_edge")

    ndvi = calculate_ndvi(nir, red)
    ndvi_matrix = _to_matrix(ndvi)
    red_matrix = _to_matrix(red)
    nir_matrix = _to_matrix(nir)
    _validate_same_shape(ndvi_matrix, red_matrix)
    _validate_same_shape(ndvi_matrix, nir_matrix)

    green_matrix = _optional_matrix(green, ndvi_matrix)
    swir_matrix = _optional_matrix(swir, ndvi_matrix)
    red_edge_matrix = _optional_matrix(red_edge, ndvi_matrix)

    mask = _build_hortifruti_mask(ndvi_matrix, red_matrix, nir_matrix, green_matrix, swir_matrix, red_edge_matrix)
    detections: List[SpectralSignatureDetection] = []

    for component in _connected_components(mask):
        if len(component) < min_pixels:
            continue
        detection = _score_component(component, ndvi_matrix, red_matrix, nir_matrix, green_matrix, swir_matrix, red_edge_matrix)
        if detection.confidence >= min_confidence:
            detections.append(detection)

    detections.sort(key=lambda item: item.confidence, reverse=True)
    return detections


def process_sentinel2_pole(
    pole_id: str,
    sentinel2_bands: Mapping[str, BandInput],
    historical_ndvi: Iterable[Any],
    *,
    obs_date: Optional[str] = None,
    culture_slug: Optional[str] = None,
    municipality: Optional[str] = None,
) -> Dict[str, Any]:
    """Run full bio-intelligence analysis for one production pole."""

    ndvi = calculate_ndvi(
        _get_band(sentinel2_bands, "B08", "nir", "NIR"),
        _get_band(sentinel2_bands, "B04", "red"),
    )
    comparison = compare_ndvi_current_vs_historical(pole_id, ndvi, historical_ndvi, obs_date=obs_date)
    signatures = recognize_spectral_signature(sentinel2_bands)
    alert = generate_supply_risk_alert(comparison, culture_slug=culture_slug, municipality=municipality)
    return {
        "pole_id": pole_id,
        "ndvi": comparison.as_dict(),
        "spectral_signatures": [signature.as_dict() for signature in signatures],
        "new_production_points": [signature.as_dict() for signature in signatures if signature.confidence >= 0.7],
        "alert": alert,
    }


def evaluate_db_supply_risk(conn: Any = None, *, lookback_days: int = 365) -> List[Dict[str, Any]]:
    """Evaluate stored FLV NDVI series and persist 'Risco de Oferta' alerts."""

    if conn is None:
        from flv.db import get_conn

        conn = get_conn()

    latest_rows = conn.execute(
        """
        SELECT n.mun_id, n.culture_id, n.obs_date, n.ndvi_value,
               m.name AS municipality, m.state_uf, m.ibge_code,
               c.slug AS culture_slug, c.name_pt AS culture_name
        FROM flv_ndvi n
        JOIN (
            SELECT mun_id, COALESCE(culture_id, -1) AS culture_key, MAX(obs_date) AS max_date
            FROM flv_ndvi
            GROUP BY mun_id, COALESCE(culture_id, -1)
        ) latest ON latest.mun_id = n.mun_id
                 AND latest.culture_key = COALESCE(n.culture_id, -1)
                 AND latest.max_date = n.obs_date
        LEFT JOIN flv_municipalities m ON m.id = n.mun_id
        LEFT JOIN flv_cultures c ON c.id = n.culture_id
        """
    ).fetchall()

    alerts = []
    for row in latest_rows:
        history = conn.execute(
            """
            SELECT ndvi_value
            FROM flv_ndvi
            WHERE mun_id = ?
              AND COALESCE(culture_id, -1) = COALESCE(?, -1)
              AND obs_date < ?
              AND obs_date >= date(?, ?)
            ORDER BY obs_date
            """,
            (row["mun_id"], row["culture_id"], row["obs_date"], row["obs_date"], f"-{lookback_days} days"),
        ).fetchall()
        historical_values = [item["ndvi_value"] for item in history]
        if not historical_values:
            continue

        pole_id = _region_key(row)
        comparison = compare_ndvi_current_vs_historical(
            pole_id,
            row["ndvi_value"],
            historical_values,
            obs_date=row["obs_date"],
        )
        alert = generate_supply_risk_alert(
            comparison,
            culture_slug=row["culture_slug"],
            municipality=_municipality_label(row),
        )
        if alert:
            _insert_alert(conn, row, alert)
            alerts.append(alert)

    conn.commit()
    return alerts


def _insert_alert(conn: Any, row: Any, alert: Mapping[str, Any]) -> None:
    existing = conn.execute(
        """
        SELECT id FROM flv_alerts
        WHERE region_key = ?
          AND alert_type = 'risco_oferta'
          AND COALESCE(culture_id, -1) = COALESCE(?, -1)
          AND created_at > datetime('now','-24 hours')
        """,
        (alert["region_key"], row["culture_id"]),
    ).fetchone()
    if existing:
        return

    conn.execute(
        """
        INSERT INTO flv_alerts (
            culture_id, mun_id, region_key, alert_type, severity,
            trigger_value, threshold_value, impact_supply_pct,
            impact_price_pct, message, valid_until
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            row["culture_id"],
            row["mun_id"],
            alert["region_key"],
            "risco_oferta",
            alert["severity"],
            alert["trigger_value"],
            alert["threshold_value"],
            alert["impact_supply_pct"],
            alert["impact_price_pct"],
            alert["message"],
            alert["valid_until"],
        ),
    )


def _build_hortifruti_mask(
    ndvi: List[List[float]],
    red: List[List[float]],
    nir: List[List[float]],
    green: Optional[List[List[float]]],
    swir: Optional[List[List[float]]],
    red_edge: Optional[List[List[float]]],
) -> List[List[bool]]:
    mask: List[List[bool]] = []
    for row_idx, row in enumerate(ndvi):
        mask_row = []
        for col_idx, value in enumerate(row):
            red_value = red[row_idx][col_idx]
            nir_value = nir[row_idx][col_idx]
            green_value = green[row_idx][col_idx] if green else None
            swir_value = swir[row_idx][col_idx] if swir else None
            red_edge_value = red_edge[row_idx][col_idx] if red_edge else None

            vigorous = 0.42 <= value <= 0.92 and nir_value > red_value
            red_edge_ok = red_edge_value is None or red_edge_value > red_value * 1.05
            moisture_ok = swir_value is None or (nir_value - swir_value) / max(nir_value + swir_value, NDVI_EPSILON) > 0.05
            green_ok = green_value is None or green_value >= red_value * 0.85
            mask_row.append(bool(vigorous and red_edge_ok and moisture_ok and green_ok))
        mask.append(mask_row)
    return mask


def _score_component(
    component: Sequence[Pixel],
    ndvi: List[List[float]],
    red: List[List[float]],
    nir: List[List[float]],
    green: Optional[List[List[float]]],
    swir: Optional[List[List[float]]],
    red_edge: Optional[List[List[float]]],
) -> SpectralSignatureDetection:
    ndvi_values = [ndvi[r][c] for r, c in component]
    rows = [r for r, _ in component]
    cols = [c for _, c in component]
    ndvi_mean = mean(ndvi_values)
    ndvi_std = pstdev(ndvi_values) if len(ndvi_values) > 1 else 0.0
    texture = _component_texture(component, ndvi)

    red_edge_values = [red_edge[r][c] for r, c in component] if red_edge else []
    swir_values = [swir[r][c] for r, c in component] if swir else []
    green_values = [green[r][c] for r, c in component] if green else []
    red_values = [red[r][c] for r, c in component]
    nir_values = [nir[r][c] for r, c in component]

    vigor_score = _clamp((ndvi_mean - 0.42) / 0.35)
    uniformity_score = _clamp(1.0 - ndvi_std / 0.18)
    texture_score = _clamp(1.0 - texture / 0.12)
    moisture_score = 0.7
    if swir_values:
        ndmi_values = [(n - s) / max(n + s, NDVI_EPSILON) for n, s in zip(nir_values, swir_values)]
        moisture_score = _clamp((mean(ndmi_values) + 0.05) / 0.35)
    red_edge_score = 0.65
    if red_edge_values:
        red_edge_score = _clamp((mean(red_edge_values) - mean(red_values)) / max(mean(red_values), NDVI_EPSILON))
    green_score = 0.65
    if green_values:
        green_score = _clamp(mean(green_values) / max(mean(red_values), NDVI_EPSILON) - 0.75)

    confidence = (
        vigor_score * 0.28
        + uniformity_score * 0.18
        + texture_score * 0.16
        + moisture_score * 0.16
        + red_edge_score * 0.14
        + green_score * 0.08
    )
    crop_type = "hortifruti_irrigado" if moisture_score >= 0.6 else "hortifruti"

    return SpectralSignatureDetection(
        crop_type=crop_type,
        confidence=_clamp(confidence),
        centroid=(round(mean(rows)), round(mean(cols))),
        pixel_count=len(component),
        ndvi_mean=ndvi_mean,
        ndvi_std=ndvi_std,
        ndvi_texture=texture,
        red_edge_mean=mean(red_edge_values) if red_edge_values else None,
        metadata={
            "vigor_score": round(vigor_score, 4),
            "uniformity_score": round(uniformity_score, 4),
            "moisture_score": round(moisture_score, 4),
            "red_edge_score": round(red_edge_score, 4),
        },
    )


def _connected_components(mask: List[List[bool]]) -> List[List[Pixel]]:
    if not mask:
        return []
    rows = len(mask)
    cols = len(mask[0])
    visited = [[False for _ in range(cols)] for _ in range(rows)]
    components: List[List[Pixel]] = []
    for row in range(rows):
        for col in range(cols):
            if visited[row][col] or not mask[row][col]:
                continue
            stack = [(row, col)]
            visited[row][col] = True
            component = []
            while stack:
                r, c = stack.pop()
                component.append((r, c))
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc] and mask[nr][nc]:
                        visited[nr][nc] = True
                        stack.append((nr, nc))
            components.append(component)
    return components


def _component_texture(component: Sequence[Pixel], matrix: List[List[float]]) -> float:
    component_set = set(component)
    diffs = []
    for row, col in component:
        value = matrix[row][col]
        for nr, nc in ((row + 1, col), (row, col + 1)):
            if (nr, nc) in component_set:
                diffs.append(abs(value - matrix[nr][nc]))
    return mean(diffs) if diffs else 0.0


def _get_band(bands: Mapping[str, BandInput], *names: str) -> BandInput:
    for name in names:
        if name in bands:
            return bands[name]
    raise KeyError(f"Sentinel-2 band required: one of {', '.join(names)}")


def _get_optional_band(bands: Mapping[str, BandInput], *names: str) -> Optional[BandInput]:
    for name in names:
        if name in bands:
            return bands[name]
    return None


def _optional_matrix(value: Optional[BandInput], reference: List[List[float]]) -> Optional[List[List[float]]]:
    if value is None:
        return None
    matrix = _to_matrix(value)
    _validate_same_shape(reference, matrix)
    return matrix


def _to_matrix(values: Any) -> List[List[float]]:
    if _np is not None and hasattr(values, "shape"):
        values = values.tolist()
    if isinstance(values, (int, float)):
        return [[float(values)]]
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise TypeError("band data must be a number or a 1D/2D numeric sequence")
    if not values:
        return []
    if all(isinstance(item, (int, float)) for item in values):
        return [[float(item) for item in values]]
    matrix = []
    for row in values:
        if not isinstance(row, Sequence) or isinstance(row, (str, bytes)):
            raise TypeError("2D band data must be a sequence of numeric rows")
        matrix.append([float(item) for item in row])
    return matrix


def _validate_same_shape(left: List[List[float]], right: List[List[float]]) -> None:
    if len(left) != len(right) or any(len(lrow) != len(rrow) for lrow, rrow in zip(left, right)):
        raise ValueError("Sentinel-2 band shapes must match")


def _mean_numeric(values: Any) -> Optional[float]:
    matrix = _to_matrix(values)
    flattened = [value for row in matrix for value in row if math.isfinite(value)]
    return mean(flattened) if flattened else None


def _region_key(row: Any) -> str:
    ibge = row["ibge_code"] or row["mun_id"]
    culture = row["culture_slug"] or "hortifruti"
    return f"{ibge}_{culture}"


def _municipality_label(row: Any) -> str:
    name = row["municipality"] or f"mun_id={row['mun_id']}"
    uf = row["state_uf"]
    return f"{name}-{uf}" if uf else name


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def to_json(payload: Any) -> str:
    """Serialize analysis payloads with stable ASCII output."""

    return json.dumps(payload, ensure_ascii=True, sort_keys=True)
