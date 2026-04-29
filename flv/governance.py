"""Governance safeguards for geographic scope, source intake and memory.

These helpers keep hard policy decisions in one place so collectors and APIs do
not accidentally drift into local-user targeting or unapproved sources.
"""

from __future__ import annotations

from urllib.parse import urlparse


GEOGRAPHIC_SCOPE = "south_america"

SOUTH_AMERICA_COUNTRIES = (
    "AR",
    "BO",
    "BR",
    "CL",
    "CO",
    "EC",
    "FK",
    "GF",
    "GY",
    "PY",
    "PE",
    "SR",
    "UY",
    "VE",
)

SOUTH_AMERICA_TERMS = (
    "south america",
    "latin america",
    "america latina",
    "américa latina",
    "america do sul",
    "américa do sul",
    "mercosul",
    "mercosur",
    "andes",
    "amazon",
    "amazonia",
    "amazônia",
    "argentina",
    "bolivia",
    "bolívia",
    "brazil",
    "brasil",
    "chile",
    "colombia",
    "colômbia",
    "ecuador",
    "equador",
    "guyana",
    "guiana",
    "paraguay",
    "paraguai",
    "peru",
    "perú",
    "suriname",
    "uruguay",
    "uruguai",
    "venezuela",
)

ELITE_SOURCES = {
    "reuters": "Reuters",
    "bloomberg": "Bloomberg",
    "bbc": "BBC",
    "al jazeera": "Al Jazeera",
    "al-jazeera": "Al Jazeera",
    "aljazeera": "Al Jazeera",
    "ibge": "IBGE",
    "sidra": "IBGE",
    "sidra-pam": "IBGE",
    "banco central": "Banco Central",
    "bcb": "Banco Central",
    "bacen": "Banco Central",
}

ALLOWED_SOURCE_NAMES = frozenset(ELITE_SOURCES.values())

ADMINISTRATIVE_MEMORY_TABLES = (
    "flv_producers_rj",
    "flv_corporate_changes",
    "flv_sovereign_reports",
)

ADMINISTRATIVE_CHANGE_TYPES = frozenset(
    {
        "diretoria",
        "socio",
        "administrador",
        "capital_social",
        "objeto_social",
        "denominacao",
        "sede",
    }
)


class SourcePolicyError(ValueError):
    """Raised when an ingestion source violates the elite-source allowlist."""


def canonical_source(source: str | None) -> str | None:
    """Return the approved display name for a source alias, if allowed."""
    if not source:
        return None

    normalized = " ".join(str(source).strip().lower().replace("_", " ").split())
    if normalized in ELITE_SOURCES:
        return ELITE_SOURCES[normalized]

    # Some rows include product suffixes, e.g. "SIDRA-PAM" or "BCB/SGS".
    for alias, canonical in ELITE_SOURCES.items():
        if normalized.startswith(alias + "/") or normalized.startswith(alias + "-"):
            return canonical

    return None


def require_elite_source(source: str | None) -> str:
    """Canonicalize a source or fail closed if it is not explicitly allowed."""
    canonical = canonical_source(source)
    if not canonical:
        allowed = ", ".join(sorted(ALLOWED_SOURCE_NAMES))
        raise SourcePolicyError(f"Fonte nao autorizada: {source!r}. Permitidas: {allowed}")
    return canonical


def filter_elite_feeds(feeds):
    """Return canonicalized feeds whose source is explicitly allowlisted."""
    approved = []
    rejected = []
    for source, url in feeds or []:
        canonical = canonical_source(source)
        if canonical:
            approved.append((canonical, url))
        else:
            rejected.append((source, url))
    return approved, rejected


def south_america_scope(user_location: str | None = None) -> dict:
    """Return the fixed continental scope; user_location is intentionally ignored."""
    return {
        "scope": GEOGRAPHIC_SCOPE,
        "countries": list(SOUTH_AMERICA_COUNTRIES),
        "user_location_ignored": bool(user_location),
    }


def has_south_america_focus(*texts: str | None) -> bool:
    """Detect whether free text points to South America as a continental scope."""
    haystack = " ".join(t or "" for t in texts).lower()
    if any(term in haystack for term in SOUTH_AMERICA_TERMS):
        return True

    # URL host/path often carries regional slugs even when a title is concise.
    for text in texts:
        if not text:
            continue
        try:
            parsed = urlparse(text)
        except Exception:
            continue
        path = f"{parsed.netloc} {parsed.path}".lower()
        if any(term.replace(" ", "-") in path for term in SOUTH_AMERICA_TERMS):
            return True

    return False
