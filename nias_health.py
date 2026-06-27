"""
NIAS — Endpoint /api/health
============================
Cole este módulo no server.py ou importe-o como nias_health.py.

Uso no server.py:
    from nias_health import checker, handle_health

    # No do_GET, antes do roteamento principal:
    if self.path == '/api/health':
        handle_health(self)
        return
"""

import json
import time
import threading
import urllib.request
import urllib.error
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler


# ---------------------------------------------------------------------------
# Configuração de fontes
# ---------------------------------------------------------------------------

SOURCES_CONFIG = {
    "cepea": {
        "url": "https://www.cepea.esalq.usp.br/br/indicador/soja.aspx",
        "method": "head",
        "stale_after": 86_400,
        "down_after":  172_800,
        "timeout": 8,
        "description": "CEPEA/ESALQ — cotações soja, milho, boi, café",
    },
    "ceasa_go": {
        "url": "https://www.ceasa.go.gov.br",
        "method": "head",
        "stale_after": 43_200,
        "down_after":  86_400,
        "timeout": 8,
        "description": "CEASA-GO — cotações hortifrutis (PDF diário)",
    },
    "ceasa_mg": {
        "url": "https://www.ceasa.mg.gov.br",
        "method": "head",
        "stale_after": 43_200,
        "down_after":  86_400,
        "timeout": 8,
        "description": "CEASA-MG — tabela HTML de cotações",
    },
    "ceasa_rn": {
        "url": "https://www.ceasa.rn.gov.br",
        "method": "head",
        "stale_after": 43_200,
        "down_after":  86_400,
        "timeout": 8,
        "description": "CEASA-RN — cotações nordeste (PDF)",
    },
    "conab": {
        "url": "https://www.conab.gov.br",
        "method": "head",
        "stale_after": 86_400,
        "down_after":  172_800,
        "timeout": 8,
        "description": "CONAB — preços mínimos de garantia",
    },
    "open_meteo": {
        "url": "https://api.open-meteo.com/v1/forecast?latitude=-15.78&longitude=-47.93&hourly=temperature_2m&forecast_days=1",
        "method": "get_json",
        "stale_after": 3_600,
        "down_after":  10_800,
        "timeout": 6,
        "description": "Open-Meteo — LAI, chuva, umidade do solo (proxy NDVI)",
    },
    "inmet": {
        "url": "https://apitempo.inmet.gov.br/token/",
        "method": "head",
        "stale_after": 7_200,
        "down_after":  21_600,
        "timeout": 8,
        "description": "INMET — estações meteorológicas brasileiras",
    },
    "bcb": {
        "url": "https://api.bcb.gov.br/dados/serie/bcdata.sgs.1/dados/ultimos/1?formato=json",
        "method": "get_json",
        "stale_after": 86_400,
        "down_after":  172_800,
        "timeout": 6,
        "description": "BCB — USD/BRL, Selic",
    },
    "ibge_sidra": {
        "url": "https://servicodados.ibge.gov.br/api/v3/agregados/6588/periodos/-1/variaveis/9606?localidades=N1[all]",
        "method": "get_json",
        "stale_after": 2_592_000,
        "down_after":  5_184_000,
        "timeout": 10,
        "description": "IBGE/SIDRA — produção agrícola municipal",
    },
    "prf_dnit": {
        "url": "https://www.gov.br/dnit/pt-br",
        "method": "head",
        "stale_after": 3_600,
        "down_after":  14_400,
        "timeout": 8,
        "description": "PRF/DNIT — condições rodoviárias e acidentes",
    },
}


# ---------------------------------------------------------------------------
# Estado global de saúde
# ---------------------------------------------------------------------------

_SOURCE_STATE: dict = {
    key: {
        "last_check_ts":     None,
        "last_ok_ts":        None,
        "last_error":        None,
        "consecutive_fails": 0,
        "http_status":       None,
        "latency_ms":        None,
    }
    for key in SOURCES_CONFIG
}

_state_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Verificação de uma fonte
# ---------------------------------------------------------------------------

def _check_source(key: str) -> None:
    cfg = SOURCES_CONFIG[key]
    t0 = time.monotonic()
    now = time.time()
    ok = False
    error_msg = None
    http_status = None

    try:
        req = urllib.request.Request(
            cfg["url"],
            headers={"User-Agent": "NIAS-HealthChecker/1.0"},
            method="HEAD" if cfg["method"] == "head" else "GET",
        )
        with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
            http_status = resp.status
            if cfg["method"] == "get_json":
                body = resp.read(4096)
                json.loads(body)
            ok = (200 <= http_status < 400)

    except urllib.error.HTTPError as e:
        http_status = e.code
        ok = (e.code < 500)
        if not ok:
            error_msg = f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        error_msg = f"URLError: {e.reason}"
    except TimeoutError:
        error_msg = f"Timeout após {cfg['timeout']}s"
    except json.JSONDecodeError:
        error_msg = "Resposta não é JSON válido"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    latency_ms = int((time.monotonic() - t0) * 1000)

    with _state_lock:
        st = _SOURCE_STATE[key]
        st["last_check_ts"] = now
        st["http_status"]   = http_status
        st["latency_ms"]    = latency_ms
        if ok:
            st["last_ok_ts"]        = now
            st["last_error"]        = None
            st["consecutive_fails"] = 0
        else:
            st["last_error"]         = error_msg
            st["consecutive_fails"] += 1


# ---------------------------------------------------------------------------
# Derivar status semântico de uma fonte
# ---------------------------------------------------------------------------

def _derive_status(key: str) -> dict:
    cfg = SOURCES_CONFIG[key]
    now = time.time()

    with _state_lock:
        st = dict(_SOURCE_STATE[key])

    last_ok = st["last_ok_ts"]
    freshness_s = int(now - last_ok) if last_ok else None

    if last_ok is None:
        status = "unknown"
    elif freshness_s > cfg["down_after"]:
        status = "down"
    elif freshness_s > cfg["stale_after"]:
        status = "stale"
    else:
        status = "ok"

    last_check = st["last_check_ts"]
    return {
        "status":            status,
        "description":       cfg["description"],
        "freshness_s":       freshness_s,
        "stale_threshold_s": cfg["stale_after"],
        "down_threshold_s":  cfg["down_after"],
        "last_check":        datetime.fromtimestamp(last_check, tz=timezone.utc).isoformat() if last_check else None,
        "last_ok":           datetime.fromtimestamp(last_ok, tz=timezone.utc).isoformat() if last_ok else None,
        "last_error":        st["last_error"],
        "consecutive_fails": st["consecutive_fails"],
        "http_status":       st["http_status"],
        "latency_ms":        st["latency_ms"],
    }


# ---------------------------------------------------------------------------
# Derivar status global do sistema
# ---------------------------------------------------------------------------

_STATUS_PRIORITY = {"down": 3, "stale": 2, "unknown": 1, "ok": 0}


def _system_status(source_statuses: dict) -> str:
    worst = max((_STATUS_PRIORITY.get(s["status"], 0) for s in source_statuses.values()), default=0)
    if worst >= 3:
        return "critical"
    if worst >= 1:
        return "degraded"
    return "ok"


# ---------------------------------------------------------------------------
# HealthChecker — probe periódico em background
# ---------------------------------------------------------------------------

class HealthChecker:
    def __init__(self, interval_s: int = 300):
        self.interval_s = interval_s
        self._timer: threading.Timer | None = None
        self._running = False

    def start(self):
        self._running = True
        self.probe_all_now()
        self._schedule_next()

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()

    def probe_all_now(self):
        threads = [
            threading.Thread(target=_check_source, args=(key,), daemon=True)
            for key in SOURCES_CONFIG
        ]
        for t in threads:
            t.start()

    def _schedule_next(self):
        if not self._running:
            return
        self._timer = threading.Timer(self.interval_s, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _tick(self):
        self.probe_all_now()
        self._schedule_next()


checker = HealthChecker(interval_s=300)


# ---------------------------------------------------------------------------
# Handler HTTP do endpoint /api/health
# ---------------------------------------------------------------------------

def handle_health(handler: BaseHTTPRequestHandler) -> None:
    """GET /api/health — público, sem autenticação."""
    source_statuses = {key: _derive_status(key) for key in SOURCES_CONFIG}

    counts: dict = {"ok": 0, "stale": 0, "down": 0, "unknown": 0}
    for s in source_statuses.values():
        counts[s["status"]] = counts.get(s["status"], 0) + 1

    # Uptime do processo (se disponível via atributo da classe handler)
    start_time = getattr(handler.__class__, '_start_time', None)
    uptime_s = int(time.time() - start_time) if start_time else None

    payload = {
        "status":     _system_status(source_statuses),
        "checked_at": datetime.now(tz=timezone.utc).isoformat(),
        "uptime_s":   uptime_s,
        "sources":    source_statuses,
        "summary": {
            "total": len(source_statuses),
            **counts,
        },
    }

    body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    handler.send_response(200)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)
