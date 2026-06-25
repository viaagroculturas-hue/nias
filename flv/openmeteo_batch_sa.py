"""
NIAS — Open-Meteo Batch para América do Sul
Busca climática em batch para todos os polos monitorados.
Uma única requisição cobre todos os pontos do continente.
"""

import json
import time
import logging
from datetime import datetime, timedelta
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

logger = logging.getLogger(__name__)

# ─── Rate-limit state (módulo-level, thread-safe suficiente para uso atual) ───
_rate_limited_until: Optional[datetime] = None
_last_fetch: Optional[datetime] = None
_cache: Optional[dict] = None
_cache_ttl_minutes = 60


def _is_rate_limited() -> bool:
    global _rate_limited_until
    if _rate_limited_until and datetime.now() < _rate_limited_until:
        return True
    _rate_limited_until = None
    return False


def _set_rate_limited(retry_after_seconds: int = 3600):
    global _rate_limited_until
    _rate_limited_until = datetime.now() + timedelta(seconds=retry_after_seconds)
    logger.warning("Open-Meteo rate limit ativo até %s", _rate_limited_until.isoformat())


def _cache_valid() -> bool:
    if _cache is None or _last_fetch is None:
        return False
    return (datetime.now() - _last_fetch).total_seconds() < _cache_ttl_minutes * 60


def fetch_south_america_weather(
    points: Optional[list] = None,
    force: bool = False,
) -> dict:
    """
    Busca dados climáticos para todos os polos sul-americanos em uma única chamada.

    Retorna dict com:
      - status: 'ok' | 'cached' | 'rate_limited' | 'error'
      - results: lista de dicts por ponto com dados climáticos
      - source: 'Open-Meteo'
      - fetched_at: ISO timestamp
    """
    global _cache, _last_fetch

    if _is_rate_limited():
        logger.info("Open-Meteo: rate limit ativo, usando cache ou retornando status.")
        return {
            "status": "rate_limited",
            "rate_limited_until": _rate_limited_until.isoformat(),
            "results": _cache.get("results", []) if _cache else [],
            "source": "Open-Meteo",
            "fetched_at": _last_fetch.isoformat() if _last_fetch else None,
        }

    if not force and _cache_valid():
        return {**_cache, "status": "cached"}

    if points is None:
        from flv.south_america_regions import get_weather_points
        points = get_weather_points()

    if not points:
        return {"status": "error", "message": "Nenhum ponto fornecido.", "results": []}

    url = _build_url(points)
    logger.info("Open-Meteo batch SA: %d pontos", len(points))

    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent": "NIAS-AgriIntel/1.0"})
            with urlopen(req, timeout=30) as resp:
                raw = json.loads(resp.read().decode())
            break
        except HTTPError as e:
            if e.code == 429:
                retry_after = int(e.headers.get("Retry-After", 3600))
                _set_rate_limited(retry_after)
                return {
                    "status": "rate_limited",
                    "rate_limited_until": _rate_limited_until.isoformat(),
                    "results": _cache.get("results", []) if _cache else [],
                    "source": "Open-Meteo",
                    "fetched_at": _last_fetch.isoformat() if _last_fetch else None,
                }
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            logger.error("Open-Meteo HTTP error %d após %d tentativas", e.code, attempt + 1)
            return {"status": "error", "message": f"HTTP {e.code}", "results": []}
        except (URLError, Exception) as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
                continue
            logger.error("Open-Meteo falhou: %s", e)
            return {"status": "error", "message": str(e), "results": []}

    results = _parse_response(raw, points)
    _cache = {
        "status": "ok",
        "results": results,
        "source": "Open-Meteo",
        "scope": "south_america",
        "total_points": len(results),
        "fetched_at": datetime.now().isoformat(),
    }
    _last_fetch = datetime.now()
    logger.info("Open-Meteo batch SA: %d resultados obtidos", len(results))
    return _cache


def _build_url(points: list) -> str:
    latitudes = ",".join(str(p["lat"]) for p in points)
    longitudes = ",".join(str(p["lon"]) for p in points)
    return (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitudes}"
        f"&longitude={longitudes}"
        "&current=temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"
        "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max"
        "&timezone=auto"
        "&forecast_days=7"
    )


def _parse_response(raw, points: list) -> list:
    """
    Open-Meteo retorna lista quando múltiplos pontos são solicitados,
    ou dict único quando apenas um ponto.
    """
    if isinstance(raw, dict):
        raw = [raw]

    results = []
    for i, (point, data) in enumerate(zip(points, raw)):
        current = data.get("current", {})
        daily = data.get("daily", {})

        results.append({
            "id": point.get("id", f"point_{i}"),
            "country_code": point.get("country_code", "??"),
            "region": point.get("region", ""),
            "lat": point["lat"],
            "lon": point["lon"],
            "source": "Open-Meteo",
            "source_type": "real",
            "fetched_at": datetime.now().isoformat(),
            "current": {
                "temperature_c": current.get("temperature_2m"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "wind_kmh": round((current.get("wind_speed_10m") or 0) * 1, 1),
                "precip_mm": current.get("precipitation"),
                "time": current.get("time"),
            },
            "forecast_7d": {
                "dates": daily.get("time", []),
                "temp_max": daily.get("temperature_2m_max", []),
                "temp_min": daily.get("temperature_2m_min", []),
                "precip_mm": daily.get("precipitation_sum", []),
                "wind_max_kmh": daily.get("wind_speed_10m_max", []),
            },
        })
    return results


def get_cache_status() -> dict:
    return {
        "cache_valid": _cache_valid(),
        "rate_limited": _is_rate_limited(),
        "rate_limited_until": _rate_limited_until.isoformat() if _rate_limited_until else None,
        "last_fetch": _last_fetch.isoformat() if _last_fetch else None,
        "cached_points": len(_cache.get("results", [])) if _cache else 0,
        "cache_ttl_minutes": _cache_ttl_minutes,
    }
