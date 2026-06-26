"""NIAS — MCP Server: expõe ferramentas NIAS via Model Context Protocol."""
import json
import time
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

from flv.db import get_conn


# ─── Manifest ─────────────────────────────────────────────────────────────────

MCP_MANIFEST = {
    "schema_version": "v1",
    "name": "nias-agro-intelligence",
    "description": "NIAS — Geographic Intelligence OS for South American Agriculture",
    "version": "2.0",
    "server_url": "https://nias.onrender.com",
    "auth": "none",
    "rate_limit": "60/min",
    "tools": [
        {
            "name": "get_price",
            "description": "Get current and historical agricultural commodity prices for SA markets",
            "parameters": {
                "type": "object",
                "properties": {
                    "product": {"type": "string", "description": "Product slug: soja, milho, tomate, cebola, etc"},
                    "region":  {"type": "string", "description": "CEASA region or state code (SP, MG, PR, etc)"},
                    "days":    {"type": "integer", "description": "Historical days to return (default 7)"},
                },
                "required": ["product"],
            },
        },
        {
            "name": "get_alerts",
            "description": "Get active agricultural alerts by severity and culture",
            "parameters": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["N1", "N2", "N3", "all"]},
                    "culture":  {"type": "string"},
                    "limit":    {"type": "integer"},
                },
            },
        },
        {
            "name": "get_climate",
            "description": "Get 7-day climate forecast for agricultural coordinates in SA",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat":  {"type": "number"},
                    "lon":  {"type": "number"},
                    "days": {"type": "integer", "default": 7},
                },
                "required": ["lat", "lon"],
            },
        },
        {
            "name": "get_arbitrage",
            "description": "Get price arbitrage opportunities between CEASA markets",
            "parameters": {
                "type": "object",
                "properties": {
                    "product":        {"type": "string", "description": "Agricultural product"},
                    "min_margin_pct": {"type": "number", "description": "Minimum viable margin %"},
                },
                "required": ["product"],
            },
        },
        {
            "name": "get_memory",
            "description": "Search NIAS market memory for similar historical events",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query about past market events"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "get_geobrain_anomaly",
            "description": "Get satellite-based crop anomaly scores for SA production poles",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {"type": "string", "default": "all"},
                },
            },
        },
        {
            "name": "calculate_carbon",
            "description": "Calculate carbon footprint for an agricultural lot",
            "parameters": {
                "type": "object",
                "properties": {
                    "product":       {"type": "string"},
                    "quantity_tons": {"type": "number"},
                    "transport_km":  {"type": "number"},
                    "organic":       {"type": "boolean"},
                },
                "required": ["product", "quantity_tons"],
            },
        },
        {
            "name": "get_route",
            "description": "Get optimal logistics route for agricultural cargo in SA",
            "parameters": {
                "type": "object",
                "properties": {
                    "product":           {"type": "string"},
                    "origin_state":      {"type": "string"},
                    "destination_state": {"type": "string"},
                    "quantity_tons":     {"type": "number"},
                    "priority":          {"type": "string", "enum": ["custo", "tempo", "segurança"]},
                },
                "required": ["product", "origin_state", "destination_state"],
            },
        },
    ],
}


# ─── Implementação de cada tool ───────────────────────────────────────────────

def _tool_get_price(params: dict) -> dict:
    product = str(params.get("product", "")).lower()
    region  = str(params.get("region", "") or "").upper()
    days    = int(params.get("days", 7))

    conn = get_conn()
    rows = []
    tables = [
        ("flv_prices",   "product", "price", "region",  "collected_at"),
        ("prices",       "product", "price", "region",  "date"),
        ("ceasa_prices", "product", "price", "ceasa",   "date"),
        ("market_prices","produto", "preco", "regiao",  "data"),
    ]
    for tbl, p_col, v_col, r_col, d_col in tables:
        try:
            where_region = f"AND UPPER({r_col}) LIKE ?" if region else ""
            args: list = [f"%{product}%"]
            if region:
                args.append(f"%{region}%")
            args.append(days)
            rows = conn.execute(
                f"""
                SELECT {p_col}, {v_col}, {r_col}, {d_col}
                FROM {tbl}
                WHERE LOWER({p_col}) LIKE ?
                  {where_region}
                  AND {d_col} >= date('now', '-' || ? || ' days')
                ORDER BY {d_col} DESC
                LIMIT 50
                """,
                args,
            ).fetchall()
            if rows:
                break
        except Exception:
            continue

    if not rows:
        return {"product": product, "region": region, "prices": [], "message": "Sem dados no período"}

    records = [{"product": r[0], "price": r[1], "region": r[2], "date": str(r[3])} for r in rows]
    prices_vals = [float(r[1]) for r in rows if r[1] is not None]
    return {
        "product":      product,
        "region":       region,
        "days":         days,
        "count":        len(records),
        "avg_price":    round(sum(prices_vals) / len(prices_vals), 2) if prices_vals else None,
        "min_price":    round(min(prices_vals), 2) if prices_vals else None,
        "max_price":    round(max(prices_vals), 2) if prices_vals else None,
        "prices":       records[:20],
    }


def _tool_get_alerts(params: dict) -> dict:
    severity = str(params.get("severity", "all") or "all").upper()
    culture  = str(params.get("culture", "") or "").lower()
    limit    = int(params.get("limit", 20))

    conn = get_conn()
    alerts = []
    tables = [
        ("flv_alerts",  "severity", "culture", "message", "created_at"),
        ("alerts",      "severity", "culture", "message", "created_at"),
        ("nias_alerts", "nivel",    "cultura", "mensagem", "data"),
    ]
    for tbl, sev_col, cul_col, msg_col, d_col in tables:
        try:
            conditions = []
            args = []
            if severity != "ALL":
                conditions.append(f"UPPER({sev_col}) = ?")
                args.append(severity)
            if culture:
                conditions.append(f"LOWER({cul_col}) LIKE ?")
                args.append(f"%{culture}%")
            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
            args.append(limit)
            rows = conn.execute(
                f"SELECT {sev_col},{cul_col},{msg_col},{d_col} FROM {tbl} {where} ORDER BY {d_col} DESC LIMIT ?",
                args,
            ).fetchall()
            if rows:
                alerts = [
                    {"severity": r[0], "culture": r[1], "message": r[2], "date": str(r[3])}
                    for r in rows
                ]
                break
        except Exception:
            continue

    return {"alerts": alerts, "count": len(alerts), "severity_filter": severity, "culture_filter": culture}


def _tool_get_climate(params: dict) -> dict:
    lat  = float(params.get("lat", -15.0))
    lon  = float(params.get("lon", -47.0))
    days = int(params.get("days", 7))

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
        f"&forecast_days={days}&timezone=America%2FSao_Paulo"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])
        prec  = daily.get("precipitation_sum", [])
        wind  = daily.get("windspeed_10m_max", [])
        forecast = [
            {
                "date":        dates[i] if i < len(dates) else None,
                "temp_max":    t_max[i]  if i < len(t_max)  else None,
                "temp_min":    t_min[i]  if i < len(t_min)  else None,
                "precip_mm":   prec[i]   if i < len(prec)   else None,
                "wind_kmh":    wind[i]   if i < len(wind)   else None,
            }
            for i in range(len(dates))
        ]
        return {"lat": lat, "lon": lon, "days": days, "forecast": forecast, "source": "open-meteo"}
    except Exception as ex:
        return {"lat": lat, "lon": lon, "error": str(ex), "forecast": []}


def _tool_get_arbitrage(params: dict) -> dict:
    try:
        from flv.arbitragem_api import _compute_arbitragem
        result = _compute_arbitragem(params.get("product", "tomate"))
        min_margin = float(params.get("min_margin_pct", 5))
        opps = [o for o in result.get("opportunities", []) if o.get("margin_pct", 0) >= min_margin]
        return {"opportunities": opps, "product": params.get("product"), "min_margin_pct": min_margin}
    except Exception:
        pass
    return {"status": "initializing", "message": "Módulo de arbitragem carregando ou sem dados suficientes"}


def _tool_get_memory(params: dict) -> dict:
    query = str(params.get("query", "") or "")
    try:
        from flv.memory_api import handle_memory_search
        # Fallback: busca simples no DB
        pass
    except Exception:
        pass

    conn = get_conn()
    results = []
    keywords = [w for w in query.lower().split() if len(w) > 3]
    tables = [
        ("market_memory", "content", "event_date", "product"),
        ("memory",        "content", "date",        "category"),
        ("nias_memory",   "texto",   "data",         "categoria"),
    ]
    for tbl, c_col, d_col, cat_col in tables:
        try:
            for kw in keywords[:3]:
                rows = conn.execute(
                    f"SELECT {c_col},{d_col},{cat_col} FROM {tbl} WHERE LOWER({c_col}) LIKE ? LIMIT 5",
                    (f"%{kw}%",),
                ).fetchall()
                for r in rows:
                    results.append({"content": r[0], "date": str(r[1]), "category": r[2]})
            if results:
                break
        except Exception:
            continue

    return {
        "query":   query,
        "results": results[:10],
        "count":   len(results),
        "source":  "nias-memory-db",
    }


def _tool_get_geobrain(params: dict) -> dict:
    region = str(params.get("region", "all") or "all")
    try:
        import importlib
        geo = importlib.import_module("flv.geobrain_api")
        if hasattr(geo, "_get_anomalies"):
            return geo._get_anomalies(region)
    except Exception:
        pass
    return {"status": "initializing", "region": region, "message": "GeoBrain carregando dados satelitais"}


def _tool_calculate_carbon(params: dict) -> dict:
    from flv.carbon_api import _compute_carbon
    return _compute_carbon(params)


def _tool_get_route(params: dict) -> dict:
    from flv.route_optimizer_api import _compute_route
    data = {
        "product":           params.get("product", "soja"),
        "origin_state":      params.get("origin_state", ""),
        "destination_state": params.get("destination_state", "SP"),
        "quantity_tons":     params.get("quantity_tons", 1),
        "priority":          params.get("priority", "custo"),
        "origin_city":       params.get("origin_city", ""),
        "destination_city":  params.get("destination_city", ""),
    }
    return _compute_route(data)


TOOL_DISPATCH = {
    "get_price":          _tool_get_price,
    "get_alerts":         _tool_get_alerts,
    "get_climate":        _tool_get_climate,
    "get_arbitrage":      _tool_get_arbitrage,
    "get_memory":         _tool_get_memory,
    "get_geobrain_anomaly": _tool_get_geobrain,
    "calculate_carbon":   _tool_calculate_carbon,
    "get_route":          _tool_get_route,
}


# ─── Handlers ─────────────────────────────────────────────────────────────────

def handle_mcp_manifest(handler, path):
    try:
        out = json.dumps(MCP_MANIFEST, ensure_ascii=False).encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(out)
    except Exception as e:
        err = json.dumps({"error": str(e)}).encode()
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(err)


def handle_mcp_tool_call(handler, path):
    try:
        length = int(handler.headers.get("Content-Length", 0))
        body   = handler.rfile.read(length) if length else b"{}"
        req    = json.loads(body or b"{}")

        tool_name = str(req.get("tool", "") or "")
        params    = req.get("parameters", {}) or {}

        if tool_name not in TOOL_DISPATCH:
            err = json.dumps({
                "tool": tool_name,
                "error": f"Tool '{tool_name}' não encontrada. Disponíveis: {list(TOOL_DISPATCH.keys())}",
                "status": "error",
            }).encode("utf-8")
            handler.send_response(404)
            handler.send_header("Content-Type", "application/json")
            handler.send_header("Access-Control-Allow-Origin", "*")
            handler.end_headers()
            handler.wfile.write(err)
            return

        t0     = time.time()
        result = TOOL_DISPATCH[tool_name](params)
        latency_ms = int((time.time() - t0) * 1000)

        response = {
            "tool":       tool_name,
            "result":     result,
            "latency_ms": latency_ms,
            "called_at":  datetime.now(timezone.utc).isoformat(),
        }
        out = json.dumps(response, ensure_ascii=False).encode("utf-8")
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(out)

    except Exception as e:
        err = json.dumps({
            "tool":   req.get("tool", "unknown") if "req" in dir() else "unknown",
            "error":  str(e),
            "status": "error",
        }, ensure_ascii=False).encode("utf-8")
        handler.send_response(500)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.end_headers()
        handler.wfile.write(err)


def handle_mcp(handler, path):
    """Router principal — despacha para manifest ou tool call."""
    parsed = urlparse(path)
    p = parsed.path.rstrip("/")

    if p.endswith("/manifest"):
        handle_mcp_manifest(handler, path)
    elif p.endswith("/tools/call"):
        handle_mcp_tool_call(handler, path)
    else:
        # Retorna manifest como default
        handle_mcp_manifest(handler, path)
