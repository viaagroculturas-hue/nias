"""Data quality helpers for FLV collectors and API queries."""
from __future__ import annotations

import re
from datetime import datetime

_DATE_RANGE_RE = re.compile(r"^(\d{2})[-/](\d{2})[-/](\d{4})\s*-\s*(\d{2})[-/](\d{2})[-/](\d{4})$")
_DMY_RE = re.compile(r"^(\d{2})[-/](\d{2})[-/](\d{4})$")
_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_date(value: object, *, range_policy: str = "end") -> str | None:
    """Return ISO YYYY-MM-DD from ISO, DD-MM-YYYY or DD-MM-YYYY - DD-MM-YYYY.

    For weekly CONAB ranges, ``range_policy='end'`` stores the week closing date,
    which is the correct point for chronological latest-price queries.
    """
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if _ISO_RE.match(text):
        try:
            return datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            return None
    m = _DATE_RANGE_RE.match(text)
    if m:
        parts = m.groups()[3:] if range_policy == "end" else m.groups()[:3]
        dd, mm, yyyy = parts
        try:
            return datetime(int(yyyy), int(mm), int(dd)).strftime("%Y-%m-%d")
        except ValueError:
            return None
    m = _DMY_RE.match(text)
    if m:
        dd, mm, yyyy = m.groups()
        try:
            return datetime(int(yyyy), int(mm), int(dd)).strftime("%Y-%m-%d")
        except ValueError:
            return None
    try:
        return datetime.fromisoformat(text[:10]).strftime("%Y-%m-%d")
    except Exception:
        return None


def valid_price(value: object, *, max_price: float = 500.0) -> float | None:
    try:
        price = float(value)
    except Exception:
        return None
    if price <= 0 or price > max_price:
        return None
    return round(price, 4)


def valid_percent(value: object, *, low: float = -100.0, high: float = 100.0) -> float | None:
    try:
        pct = float(value)
    except Exception:
        return None
    if pct < low or pct > high:
        return None
    return pct


def quality_for_source(source: str | None) -> tuple[int, str]:
    src = (source or "").lower()
    if any(token in src for token in ["synthetic", "simulado", "ref", "proxy", "fallback", "best-effort", "update-"]):
        return 1, "synthetic_or_proxy"
    return 0, "official_or_observed"


def date_order_expr(column: str) -> str:
    """SQLite expression for robust ordering of mixed legacy date strings."""
    return (
        f"COALESCE(date({column}), "
        f"date(substr({column}, 18, 4) || '-' || substr({column}, 15, 2) || '-' || substr({column}, 12, 2)), "
        f"date(substr({column}, 7, 4) || '-' || substr({column}, 4, 2) || '-' || substr({column}, 1, 2)))"
    )
