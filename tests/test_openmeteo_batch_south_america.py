"""
Testes: Open-Meteo batch para América do Sul.
Valida estrutura sem fazer chamadas de rede reais.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from unittest.mock import patch, MagicMock
from flv.openmeteo_batch_sa import (
    _build_url,
    _parse_response,
    get_cache_status,
    fetch_south_america_weather,
)
from flv.south_america_regions import get_weather_points


SAMPLE_POINTS = [
    {"id": "BR-SP-CIN", "lat": -23.52, "lon": -46.19, "country_code": "BR", "region": "Cinturão Verde SP"},
    {"id": "AR-MDZ-CEN", "lat": -32.89, "lon": -68.84, "country_code": "AR", "region": "Mendoza"},
    {"id": "CL-OHI-FRU", "lat": -34.17, "lon": -70.74, "country_code": "CL", "region": "O'Higgins"},
]

SAMPLE_API_RESPONSE = [
    {
        "current": {"temperature_2m": 22.5, "relative_humidity_2m": 65, "wind_speed_10m": 12.3, "precipitation": 0.0, "time": "2026-06-25T12:00"},
        "daily": {"time": ["2026-06-25"], "temperature_2m_max": [25.0], "temperature_2m_min": [15.0], "precipitation_sum": [0.0], "wind_speed_10m_max": [20.0]},
    },
    {
        "current": {"temperature_2m": 10.1, "relative_humidity_2m": 45, "wind_speed_10m": 18.0, "precipitation": 0.0, "time": "2026-06-25T12:00"},
        "daily": {"time": ["2026-06-25"], "temperature_2m_max": [14.0], "temperature_2m_min": [4.0], "precipitation_sum": [0.0], "wind_speed_10m_max": [25.0]},
    },
    {
        "current": {"temperature_2m": 12.0, "relative_humidity_2m": 70, "wind_speed_10m": 8.0, "precipitation": 1.2, "time": "2026-06-25T12:00"},
        "daily": {"time": ["2026-06-25"], "temperature_2m_max": [16.0], "temperature_2m_min": [6.0], "precipitation_sum": [1.2], "wind_speed_10m_max": [15.0]},
    },
]


def test_build_url_contains_all_coordinates():
    url = _build_url(SAMPLE_POINTS)
    assert "latitude=" in url
    assert "longitude=" in url
    assert "-23.52" in url
    assert "-32.89" in url
    assert "-34.17" in url
    assert "open-meteo.com" in url


def test_build_url_single_request_for_multiple_points():
    url = _build_url(SAMPLE_POINTS)
    # Deve ser uma única URL, não múltiplas
    assert url.count("https://api.open-meteo.com") == 1
    # Coordenadas separadas por vírgula
    assert "," in url.split("latitude=")[1].split("&")[0]


def test_parse_response_returns_one_per_point():
    results = _parse_response(SAMPLE_API_RESPONSE, SAMPLE_POINTS)
    assert len(results) == len(SAMPLE_POINTS)


def test_parse_response_structure():
    results = _parse_response(SAMPLE_API_RESPONSE, SAMPLE_POINTS)
    for r in results:
        assert "id" in r
        assert "country_code" in r
        assert "current" in r
        assert "forecast_7d" in r
        assert "source" in r
        assert r["source"] == "Open-Meteo"
        assert r["source_type"] == "real"
        curr = r["current"]
        assert "temperature_c" in curr
        assert "humidity_pct" in curr


def test_parse_response_preserves_country():
    results = _parse_response(SAMPLE_API_RESPONSE, SAMPLE_POINTS)
    assert results[0]["country_code"] == "BR"
    assert results[1]["country_code"] == "AR"
    assert results[2]["country_code"] == "CL"


def test_fetch_returns_rate_limited_without_network():
    """Simula rate limit ativo — não deve fazer chamada de rede."""
    import flv.openmeteo_batch_sa as mod
    from datetime import datetime, timedelta
    original = mod._rate_limited_until
    mod._rate_limited_until = datetime.now() + timedelta(hours=1)
    try:
        result = fetch_south_america_weather(points=SAMPLE_POINTS)
        assert result["status"] == "rate_limited"
        assert "rate_limited_until" in result
    finally:
        mod._rate_limited_until = original


def test_fetch_uses_cache():
    """Com cache válido, não deve chamar rede."""
    import flv.openmeteo_batch_sa as mod
    from datetime import datetime
    mod._cache = {"status": "ok", "results": [{"id": "cached"}], "total_points": 1}
    mod._last_fetch = datetime.now()
    mod._rate_limited_until = None
    try:
        result = fetch_south_america_weather(points=SAMPLE_POINTS, force=False)
        assert result["status"] == "cached"
        assert result["results"][0]["id"] == "cached"
    finally:
        mod._cache = None
        mod._last_fetch = None


def test_cache_status_structure():
    status = get_cache_status()
    assert "cache_valid" in status
    assert "rate_limited" in status
    assert "cache_ttl_minutes" in status


def test_weather_points_count_is_adequate():
    pts = get_weather_points()
    assert len(pts) >= 30, "Deve ter pelo menos 30 polos monitorados na América do Sul"


def test_no_duplicate_ids():
    pts = get_weather_points()
    ids = [p["id"] for p in pts]
    assert len(ids) == len(set(ids)), "IDs de polos não devem ser duplicados"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
