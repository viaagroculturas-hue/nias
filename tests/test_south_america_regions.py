"""
Testes: configuração de regiões sul-americanas do NIAS.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flv.south_america_regions import (
    SOUTH_AMERICA_REGIONS,
    MONITORED_COUNTRIES,
    get_all_regions,
    get_regions_by_country,
    get_weather_points,
    get_country_codes,
    summary,
    SCOPE,
    SCOPE_LABEL,
    SYSTEM_FULL_NAME,
)

REQUIRED_COUNTRIES = ["BR", "AR", "CL", "PE", "BO", "PY", "UY", "CO", "EC"]


def test_scope_is_south_america():
    assert SCOPE == "south_america"
    assert "América do Sul" in SCOPE_LABEL
    assert "América do Sul" in SYSTEM_FULL_NAME
    assert "NIAS" in SYSTEM_FULL_NAME


def test_all_required_countries_present():
    codes = get_country_codes()
    for cc in REQUIRED_COUNTRIES:
        assert cc in codes, f"País {cc} ausente em MONITORED_COUNTRIES"


def test_brazil_has_regions():
    br = get_regions_by_country("BR")
    assert len(br) >= 5, "Brasil deve ter ao menos 5 polos"
    names = [r["region"] for r in br]
    assert any("Sul de Minas" in n for n in names)
    assert any("Cristalina" in n for n in names)


def test_argentina_has_regions():
    ar = get_regions_by_country("AR")
    assert len(ar) >= 3
    assert any("Mendoza" in r["region"] for r in ar)


def test_chile_has_regions():
    cl = get_regions_by_country("CL")
    assert len(cl) >= 2
    assert any("O'Higgins" in r["region"] for r in cl)


def test_peru_has_regions():
    pe = get_regions_by_country("PE")
    assert len(pe) >= 2
    assert any("Ica" in r["region"] for r in pe)


def test_paraguay_has_regions():
    py = get_regions_by_country("PY")
    assert len(py) >= 1


def test_uruguay_has_regions():
    uy = get_regions_by_country("UY")
    assert len(uy) >= 1


def test_bolivia_has_regions():
    bo = get_regions_by_country("BO")
    assert len(bo) >= 1
    assert any("Santa Cruz" in r["region"] for r in bo)


def test_all_regions_have_required_fields():
    required = ["id", "country", "country_code", "region", "lat", "lon", "products", "importance"]
    for r in SOUTH_AMERICA_REGIONS:
        for field in required:
            assert field in r, f"Campo '{field}' ausente em {r.get('id', '?')}"
        assert isinstance(r["products"], list)
        assert -90 <= r["lat"] <= 90
        assert -180 <= r["lon"] <= 180


def test_weather_points_structure():
    pts = get_weather_points()
    assert len(pts) == len(SOUTH_AMERICA_REGIONS)
    for p in pts:
        assert "lat" in p and "lon" in p
        assert "id" in p
        assert "country_code" in p


def test_summary():
    s = summary()
    assert s["scope"] == "south_america"
    assert s["total_regions"] >= 30
    assert s["countries"] >= 9
    for cc in REQUIRED_COUNTRIES:
        assert cc in s["by_country"], f"País {cc} sem regiões no summary"


def test_brazil_not_removed():
    br = get_regions_by_country("BR")
    assert len(br) >= 10, "Brasil deve ter pelo menos 10 polos preservados"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
