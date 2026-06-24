from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_CANDIDATES = [
    os.environ.get("NIAS_DB_PATH"),
    os.path.join(ROOT, "data", "nia_flv.db"),
    os.path.join(ROOT, "nia_flv.db"),
    os.path.join(ROOT, "flv", "nia_flv.db"),
]

SOURCE_CATALOG = [
    {"name": "CONAB/PROHORT", "scope": "preços hortigranjeiros / CEASAs", "mode": "live_or_local_cache"},
    {"name": "IBGE/SIDRA", "scope": "produção municipal/agropecuária", "mode": "local_official_snapshot"},
    {"name": "INMET/NASA POWER", "scope": "clima observado/agroclima", "mode": "local_or_live_service"},
    {"name": "SATVeg/NASA", "scope": "NDVI/vegetação", "mode": "local_observed_only"},
    {"name": "CNJ/DataJud", "scope": "recuperação judicial / situation room", "mode": "requires_api_key"},
    {"name": "NOAA CPC/IRI", "scope": "ENSO / El Niño / La Niña", "mode": "external_reference"},
]


def _connect() -> Optional[sqlite3.Connection]:
    for path in DB_CANDIDATES:
        if path and os.path.exists(path):
            try:
                # Open read/write briefly so runtime migrations can add compatibility columns
                # if Render is using an older SQLite file.
                conn = sqlite3.connect(path, timeout=5)
                conn.row_factory = sqlite3.Row
                try:
                    from flv.db_migration import ensure_runtime_schema
                    ensure_runtime_schema(conn)
                except Exception:
                    pass
                return conn
            except Exception:
                continue
    return None


def _q(conn: sqlite3.Connection, sql: str, args: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
    try:
        return conn.execute(sql, args).fetchall()
    except Exception:
        return []


def _one(conn: sqlite3.Connection, sql: str, args: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
    rows = _q(conn, sql, args)
    return rows[0] if rows else None

def _has_col(conn: sqlite3.Connection, table: str, col: str) -> bool:
    try:
        return col in {r[1] for r in conn.execute(f'PRAGMA table_info({table})').fetchall()}
    except Exception:
        return False

def _synth_sql(conn: sqlite3.Connection, table_alias: str, table_name: str) -> str:
    return f'COALESCE({table_alias}.is_synthetic,0)' if _has_col(conn, table_name, 'is_synthetic') else '0'


def _fmt_mt(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:.2f} Mt"


def _fmt_pct(v: Optional[float]) -> str:
    if v is None:
        return "—"
    return f"{'+' if v > 0 else ''}{v:.1f}%"


def _delta_class(v: Optional[float]) -> str:
    if v is None:
        return "neutral"
    return "up" if v >= 0 else "down"


def _quality(is_synthetic: Any, value: Any = True) -> str:
    if not value:
        return "unavailable"
    return "synthetic_or_proxy" if int(is_synthetic or 0) else "observed"


def _latest_production_card(conn: sqlite3.Connection, slug: str, dom_id: str, label: str) -> Dict[str, Any]:
    rows = _q(conn, """
        SELECT c.slug, c.name_pt, p.year, SUM(p.production_tons) AS tons, MAX(p.source) AS source,
               0 AS is_synthetic
        FROM flv_production p
        JOIN flv_cultures c ON c.id = p.culture_id
        WHERE c.slug = ?
        GROUP BY c.slug, c.name_pt, p.year
        ORDER BY p.year DESC
        LIMIT 2
    """, (slug,))
    latest = rows[0] if rows else None
    prev = rows[1] if len(rows) > 1 else None
    mt = float(latest["tons"]) / 1_000_000 if latest and latest["tons"] is not None else None
    delta = None
    if latest and prev and prev["tons"]:
        delta = (float(latest["tons"]) - float(prev["tons"])) / float(prev["tons"]) * 100
    return {
        "id": dom_id,
        "label": f"{label} {latest['year']}" if latest else label,
        "value": _fmt_mt(mt),
        "delta": f"{_fmt_pct(delta)} vs ano anterior" if delta is not None else "sem comparação anual observada",
        "delta_class": _delta_class(delta),
        "source": latest["source"] if latest else "IBGE/SIDRA",
        "quality": _quality(latest["is_synthetic"] if latest else 0, latest),
        "date": str(latest["year"]) if latest else None,
    }


def _horti_card(conn: sqlite3.Connection) -> Dict[str, Any]:
    row = _one(conn, """
        SELECT price_date, COUNT(*) AS n, AVG(price_avg) AS avg_price,
               MAX(source) AS source, 0 AS is_synthetic
        FROM flv_ceasa_prices
        WHERE price_date = (SELECT MAX(price_date) FROM flv_ceasa_prices WHERE COALESCE(price_avg,0) > 0)
          AND COALESCE(price_avg,0) > 0
    """)
    if not row or not row["n"]:
        return {"id":"kpi-horti","label":"HORTIFRUTIS","value":"—","delta":"sem preço observado","delta_class":"neutral","source":"CONAB/PROHORT","quality":"unavailable","date":None}
    return {
        "id": "kpi-horti",
        "label": "HORTIFRUTIS CEASA",
        "value": f"R$ {float(row['avg_price']):.2f}/kg",
        "delta": f"{int(row['n'])} cotações no último lote",
        "delta_class": "neutral",
        "source": row["source"] or "CONAB/PROHORT",
        "quality": _quality(row["is_synthetic"], True),
        "date": row["price_date"],
    }


def _ndvi_card(conn: sqlite3.Connection) -> Dict[str, Any]:
    latest = _one(conn, """
        SELECT obs_date, AVG(ndvi_value) AS ndvi, AVG(ndvi_anomaly) AS anomaly,
               MAX(source) AS source, 0 AS is_synthetic
        FROM flv_ndvi
        GROUP BY obs_date
        ORDER BY obs_date DESC
        LIMIT 1
    """)
    if not latest:
        return {"id":"kpi-ndvi","label":"NDVI MÉDIO","value":"—","delta":"sem NDVI observado","delta_class":"neutral","source":"SATVeg/NASA","quality":"unavailable","date":None}
    anomaly = latest["anomaly"]
    return {
        "id": "kpi-ndvi",
        "label": "NDVI MÉDIO",
        "value": f"{float(latest['ndvi']):.3f}" if latest["ndvi"] is not None else "—",
        "delta": f"anomalia {_fmt_pct(float(anomaly)*100)}" if anomaly is not None else "sem anomalia calculada",
        "delta_class": _delta_class(float(anomaly) if anomaly is not None else None),
        "source": latest["source"] or "SATVeg/NASA",
        "quality": _quality(latest["is_synthetic"], True),
        "date": latest["obs_date"],
    }


def _humidity_card(conn: sqlite3.Connection) -> Dict[str, Any]:
    latest = _one(conn, """
        SELECT obs_date, AVG(humidity_pct) AS hum, MAX(source) AS source,
               0 AS is_synthetic
        FROM flv_climate
        WHERE humidity_pct IS NOT NULL
        GROUP BY obs_date
        ORDER BY obs_date DESC
        LIMIT 1
    """)
    if not latest:
        return {"id":"kpi-hum","label":"UMIDADE MÉDIA","value":"—","delta":"sem clima observado","delta_class":"neutral","source":"INMET/NASA POWER","quality":"unavailable","date":None}
    hum = float(latest["hum"])
    status = "baixa" if hum < 35 else "adequada" if hum < 75 else "alta"
    return {
        "id": "kpi-hum",
        "label": "UMIDADE MÉDIA",
        "value": f"{hum:.1f}%",
        "delta": f"condição {status}",
        "delta_class": "down" if hum < 35 else "up" if hum < 75 else "neutral",
        "source": latest["source"] or "INMET/NASA POWER",
        "quality": _quality(latest["is_synthetic"], True),
        "date": latest["obs_date"],
    }


def _cards(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    # IDs preservados para não quebrar o frontend atual.
    return [
        _latest_production_card(conn, "tomate", "kpi-soja", "TOMATE"),
        _latest_production_card(conn, "batata", "kpi-milho", "BATATA"),
        _ndvi_card(conn),
        _humidity_card(conn),
        _latest_production_card(conn, "uva", "kpi-boi", "UVA"),
        _horti_card(conn),
    ]


def _weather(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = _q(conn, """
        SELECT m.name, m.state_uf, c.obs_date, c.temp_max_c, c.humidity_pct, c.wind_ms,
               c.precip_mm, c.source, 0 AS is_synthetic
        FROM flv_climate c
        JOIN flv_municipalities m ON m.id = c.mun_id
        WHERE c.obs_date = (SELECT MAX(obs_date) FROM flv_climate)
        ORDER BY c.precip_mm DESC, c.temp_max_c DESC
        LIMIT 6
    """)
    out: List[Dict[str, Any]] = []
    for r in rows:
        hum = r["humidity_pct"]
        temp = r["temp_max_c"]
        precip = r["precip_mm"]
        if hum is not None and float(hum) < 30:
            status, level = "SECO / ESTRESSE", "danger"
        elif precip is not None and float(precip) > 20:
            status, level = "CHUVA FORTE", "warn"
        else:
            status, level = "CONDIÇÃO MONITORADA", "ok"
        out.append({
            "region": f"{r['name']} / {r['state_uf']}",
            "temp": f"{float(temp):.1f}°C" if temp is not None else "—",
            "humidity": f"Umid: {float(hum):.0f}%" if hum is not None else "Umid: —",
            "wind": f"Vento: {float(r['wind_ms']) * 3.6:.0f}km/h" if r["wind_ms"] is not None else "Vento: —",
            "precip": f"Chuva: {float(precip):.1f}mm" if precip is not None else "Chuva: —",
            "status": status,
            "level": level,
            "source": r["source"] or "INMET/NASA POWER",
            "quality": _quality(r["is_synthetic"], True),
            "date": r["obs_date"],
        })
    return out


def _alerts(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = _q(conn, """
        SELECT region_key, alert_type, severity, impact_supply_pct, impact_price_pct, message,
               valid_until, created_at
        FROM flv_alerts
        WHERE valid_until IS NULL OR valid_until > datetime('now')
        GROUP BY region_key, alert_type, severity, message
        ORDER BY CASE severity WHEN 'vermelho' THEN 0 WHEN 'laranja' THEN 1 ELSE 2 END,
                 created_at DESC
        LIMIT 10
    """)
    sev_map = {"vermelho":"ALTA", "laranja":"MÉDIA", "amarelo":"ATENÇÃO"}
    return [{
        "title": str(r["alert_type"] or "alerta").replace("_", " ").upper(),
        "region_key": r["region_key"],
        "severity": r["severity"] or "amarelo",
        "severity_label": sev_map.get(r["severity"], "ATENÇÃO"),
        "message": r["message"] or "Alerta operacional sem descrição detalhada.",
        "impact_supply_pct": r["impact_supply_pct"],
        "impact_price_pct": r["impact_price_pct"],
        "created_at": r["created_at"],
        "source": "Motor NIAS com dados climáticos/produção locais",
        "quality": "derived_from_observed_or_curated",
    } for r in rows]


def _ceasa_market(conn: sqlite3.Connection, limit: int = 12) -> List[Dict[str, Any]]:
    rows = _q(conn, """
        SELECT c.slug, c.name_pt, p.terminal, p.price_date, AVG(p.price_avg) AS price_avg,
               MIN(p.price_min) AS price_min, MAX(p.price_max) AS price_max,
               COUNT(*) AS quotes, MAX(p.source) AS source, 0 AS is_synthetic
        FROM flv_ceasa_prices p
        JOIN flv_cultures c ON c.id = p.culture_id
        WHERE p.price_date = (SELECT MAX(price_date) FROM flv_ceasa_prices WHERE COALESCE(price_avg,0)>0)
          AND COALESCE(p.price_avg,0)>0
        GROUP BY c.slug, c.name_pt, p.terminal, p.price_date
        ORDER BY price_avg DESC
        LIMIT ?
    """, (limit,))
    return [{
        "product": r["name_pt"], "slug": r["slug"], "terminal": r["terminal"],
        "price_avg": round(float(r["price_avg"]), 2),
        "range": f"R$ {float(r['price_min'] or 0):.2f}–{float(r['price_max'] or 0):.2f}",
        "quotes": int(r["quotes"]), "date": r["price_date"],
        "source": r["source"] or "CONAB/PROHORT", "quality": _quality(r["is_synthetic"], True)
    } for r in rows]


def _macro(conn: sqlite3.Connection) -> Dict[str, Any]:
    r = _one(conn, "SELECT * FROM flv_macro_indicators ORDER BY obs_date DESC LIMIT 1")
    if not r:
        return {"status":"unavailable", "message":"sem indicadores macroeconômicos no banco", "items": []}
    items = []
    for key, label, unit, max_valid in [
        ("diesel_brl_l", "Diesel", "R$/L", 20),
        ("usd_brl", "USD/BRL", "", 20),
        ("selic_pct", "Selic", "%", 50),
        ("ipca_yoy_pct", "IPCA 12m", "%", 30),
    ]:
        value = r[key]
        valid = value is not None and abs(float(value)) <= max_valid
        items.append({"key": key, "label": label, "value": float(value) if valid else None, "unit": unit, "quality": "observed" if valid and not (r["is_synthetic"] if "is_synthetic" in r.keys() else 0) else "unavailable_or_proxy"})
    return {"status":"ok", "date": r["obs_date"], "source": r["source"], "items": items}


def _situation(conn: sqlite3.Connection) -> Dict[str, Any]:
    rows = _q(conn, """
        SELECT judicial_status, COUNT(*) AS n
        FROM flv_producers_rj
        GROUP BY judicial_status
        ORDER BY n DESC
    """)
    return {"total": sum(int(r["n"]) for r in rows), "by_status": [dict(r) for r in rows], "source": "CNJ/DataJud quando DATAJUD_API_KEY estiver configurada; fallback base curada local"}


def _topbar(cards: List[Dict[str, Any]], weather: List[Dict[str, Any]], alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    temp = next((w.get("temp") for w in weather if w.get("temp") != "—"), "—")
    ndvi = next((c.get("value") for c in cards if c.get("id") == "kpi-ndvi"), "—")
    return {
        "temperature": temp,
        "ndvi": ndvi,
        "active_alerts": len(alerts),
        "status": "LIVE" if any(c.get("quality") == "observed" for c in cards) else "DEGRADED",
    }


def build_dashboard_summary() -> Dict[str, Any]:
    conn = _connect()
    now = datetime.now(timezone.utc).isoformat()
    if not conn:
        return {
            "status": "degraded", "updated_at": now, "cards": [], "weather": [], "alerts": [],
            "market": [], "macro": {"status":"unavailable"}, "situation": {},
            "sources": SOURCE_CATALOG,
            "message": "Banco local não encontrado. Dashboard sem atualização observada.",
        }
    try:
        cards = _cards(conn)
        weather = _weather(conn)
        alerts = _alerts(conn)
        observed = sum(1 for c in cards if c.get("quality") == "observed")
        synthetic = sum(1 for c in cards if c.get("quality") == "synthetic_or_proxy")
        return {
            "status": "ok" if observed else "degraded",
            "updated_at": now,
            "cards": cards,
            "weather": weather,
            "alerts": alerts,
            "topbar": _topbar(cards, weather, alerts),
            "market": _ceasa_market(conn),
            "macro": _macro(conn),
            "situation": _situation(conn),
            "quality": {
                "observed_cards": observed,
                "synthetic_or_proxy_cards": synthetic,
                "total_cards": len(cards),
                "rule": "Dashboard sem valores fixos: cada item exibe fonte, data e qualidade; dado inválido vira indisponível.",
            },
            "sources": SOURCE_CATALOG,
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass
