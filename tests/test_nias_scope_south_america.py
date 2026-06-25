"""
Testes: escopo sul-americano do NIAS API.
Valida endpoints, filtros por país e premissa continental.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ─── helpers ──────────────────────────────────────────────────────

def _dispatch(path, params=None):
    from flv.nias_api.router import _dispatch as d
    return d(path, params or {})


# ─── testes de premissa ───────────────────────────────────────────

def test_status_has_south_america_scope():
    r = _dispatch("status")
    assert r.get("status") == "ok"
    data = r.get("data", {})
    assert data.get("scope") == "south_america" or data.get("scope_label") is not None


def test_docs_description_mentions_america_do_sul():
    r = _dispatch("docs")
    assert r.get("status") == "ok"
    data = r.get("data", {})
    desc = data.get("description", "")
    assert "América do Sul" in desc or "South America" in desc


def test_docs_lists_regions_endpoint():
    r = _dispatch("docs")
    endpoints = r.get("data", {}).get("endpoints", [])
    paths = [e["path"] for e in endpoints]
    assert any("regions" in p for p in paths)


def test_regions_endpoint_returns_all_countries():
    r = _dispatch("regions")
    assert r.get("status") == "ok"
    data = r.get("data", {})
    assert data.get("scope") == "south_america"
    assert data.get("total", 0) >= 30
    by_country = data.get("by_country", {})
    for cc in ["BR", "AR", "CL", "PE", "BO", "PY", "UY"]:
        assert cc in by_country, f"País {cc} ausente em /api/nias/regions"


def test_regions_filter_by_brazil():
    r = _dispatch("regions", {"country": ["BR"]})
    assert r.get("status") == "ok"
    data = r.get("data", {})
    assert data.get("country") == "BR"
    regions = data.get("regions", [])
    assert all(reg["country_code"] == "BR" for reg in regions)
    assert len(regions) >= 5


def test_regions_filter_by_argentina():
    r = _dispatch("regions", {"country": ["AR"]})
    assert r.get("status") == "ok"
    data = r.get("data", {})
    assert data.get("country") == "AR"
    regions = data.get("regions", [])
    assert len(regions) >= 3


def test_regions_south_america_alias():
    r1 = _dispatch("regions")
    r2 = _dispatch("regions/south-america")
    assert r1.get("status") == "ok"
    assert r2.get("status") == "ok"
    assert r1.get("data", {}).get("total") == r2.get("data", {}).get("total")


def test_intelligence_weather_price_accepts_scope_param():
    r = _dispatch("intelligence/weather-price", {"scope": ["south_america"]})
    # Não deve retornar 404 ou erro de parâmetro
    assert r.get("status") in ("ok", "partial")
    data = r.get("data", {})
    scope = data.get("scope", "")
    assert scope == "south_america" or scope == ""


def test_intelligence_weather_price_accepts_country_param():
    r = _dispatch("intelligence/weather-price", {"country": ["BR"]})
    assert r.get("status") in ("ok", "partial")


def test_no_user_location_as_center():
    """O sistema não deve centrar análise em geolocalização do usuário."""
    r = _dispatch("regions")
    data = r.get("data", {})
    # O scope deve ser continental, não baseado em localização
    assert data.get("scope") == "south_america"
    assert "user_location" not in data
    assert "geolocation" not in data


def test_brazil_still_in_regions():
    """Brasil não deve ter sido removido."""
    r = _dispatch("regions", {"country": ["BR"]})
    regions = r.get("data", {}).get("regions", [])
    assert len(regions) >= 5, "Brasil foi removido ou perdeu regiões"


def test_weather_south_america_endpoint_exists():
    """Endpoint de clima batch sul-americano deve existir (pode ser partial sem rede)."""
    r = _dispatch("weather/south-america")
    assert r.get("status") in ("ok", "partial", "cached")


def test_docs_scope_field():
    r = _dispatch("docs")
    data = r.get("data", {})
    assert data.get("scope") == "south_america"
    assert data.get("scope_label") == "América do Sul"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
