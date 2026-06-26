"""
Push Alerts API — Sistema de alertas push com webhooks e registro in-memory.

Endpoints:
  GET  /api/alerts/status
  POST /api/alerts/subscribe   body: {webhook_url, events, min_vfr}
  GET  /api/alerts/history
  POST /api/alerts/test
"""
import json, os, time, threading, re, uuid
from datetime import datetime, timezone
import urllib.request

# ── Estado global ─────────────────────────────────────────────────────────────
_lock = threading.Lock()

# {webhook_url: {"events": list|None, "min_vfr": float|None, "registered_at": iso}}
_SUBSCRIBERS = {}

# Lista circular de alertas disparados (max 500)
_HISTORY = []
_MAX_HISTORY = 500

# Contadores
_STATS = {
    "alerts_dispatched": 0,
    "webhook_successes": 0,
    "webhook_failures":  0,
    "started_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_url(url):
    return bool(re.match(r"^https?://[^\s/$.?#].[^\s]*$", url or ""))


def _make_alert_id():
    return f"{int(time.time()*1000)}-{str(uuid.uuid4())[:8]}"


def _post_webhook(url, payload_bytes):
    """Dispara POST para webhook. Ignora falhas (fire-and-forget)."""
    try:
        req = urllib.request.Request(
            url,
            data=payload_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "NIAS-AlertBot/1.0"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5):
            pass
        return True
    except Exception:
        return False


def _should_dispatch(subscriber, alert):
    """Verifica se o subscriber deve receber o alerta conforme filtros."""
    cfg = subscriber
    events = cfg.get("events")
    if events and alert.get("event_type") not in events:
        return False
    min_vfr = cfg.get("min_vfr")
    if min_vfr is not None:
        try:
            if float(alert.get("vfr_brl", 0)) < float(min_vfr):
                return False
        except (TypeError, ValueError):
            pass
    return True


class _PushAlerts:
    """Singleton para dispatch de alertas — importável por outros módulos."""

    def dispatch(self, alert_dict):
        """
        Dispara um alerta para todos os subscribers elegíveis.
        alert_dict deve conter os campos do schema de alerta.
        """
        # Garante campos mínimos
        alert = {
            "id":             alert_dict.get("id", _make_alert_id()),
            "event_type":     alert_dict.get("event_type", "generic"),
            "severity":       alert_dict.get("severity", "N2"),
            "title":          alert_dict.get("title", "Alerta NIAS"),
            "description":    alert_dict.get("description", ""),
            "culture":        alert_dict.get("culture", ""),
            "region":         alert_dict.get("region", ""),
            "vfr_brl":        alert_dict.get("vfr_brl", 0.0),
            "recommendation": alert_dict.get("recommendation", ""),
            "timestamp":      alert_dict.get("timestamp", _now_iso()),
        }

        payload = json.dumps(alert, ensure_ascii=False).encode("utf-8")

        successes = 0
        failures  = 0

        with _lock:
            subscribers_snapshot = dict(_SUBSCRIBERS)

        threads = []
        results = {}

        def _fire(url, cfg):
            if _should_dispatch(cfg, alert):
                ok = _post_webhook(url, payload)
                results[url] = ok

        for url, cfg in subscribers_snapshot.items():
            t = threading.Thread(target=_fire, args=(url, cfg), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=7)

        for ok in results.values():
            if ok:
                successes += 1
            else:
                failures += 1

        with _lock:
            _HISTORY.append(alert)
            if len(_HISTORY) > _MAX_HISTORY:
                _HISTORY.pop(0)
            _STATS["alerts_dispatched"] += 1
            _STATS["webhook_successes"]  += successes
            _STATS["webhook_failures"]   += failures

        return {"dispatched": len(results), "successes": successes, "failures": failures}


# Singleton exportável
PUSH_ALERTS = _PushAlerts()


# ── Handlers HTTP ─────────────────────────────────────────────────────────────

def _read_body(handler):
    length = int(handler.headers.get("Content-Length", 0))
    if length:
        return json.loads(handler.rfile.read(length).decode("utf-8"))
    return {}


def _send_json(handler, code, obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


def handle_alerts_status(handler, path):
    try:
        with _lock:
            subs = len(_SUBSCRIBERS)
            stats = dict(_STATS)
        result = {
            "status":            "operational",
            "subscribers_count": subs,
            "alerts_dispatched": stats["alerts_dispatched"],
            "webhook_successes": stats["webhook_successes"],
            "webhook_failures":  stats["webhook_failures"],
            "history_count":     len(_HISTORY),
            "started_at":        stats["started_at"],
            "checked_at":        _now_iso(),
        }
        _send_json(handler, 200, result)
    except Exception as e:
        _send_json(handler, 500, {"error": str(e)})


def handle_alerts_subscribe(handler, path):
    try:
        body = _read_body(handler)
        webhook_url = body.get("webhook_url", "").strip()
        if not _validate_url(webhook_url):
            _send_json(handler, 400, {"error": "webhook_url inválido"})
            return

        events  = body.get("events")   # lista ou None
        min_vfr = body.get("min_vfr")  # float ou None

        cfg = {
            "events":        events,
            "min_vfr":       min_vfr,
            "registered_at": _now_iso(),
        }

        with _lock:
            _SUBSCRIBERS[webhook_url] = cfg

        _send_json(handler, 200, {
            "ok":          True,
            "webhook_url": webhook_url,
            "config":      cfg,
            "message":     "Subscriber registrado com sucesso.",
        })
    except Exception as e:
        _send_json(handler, 500, {"error": str(e)})


def handle_alerts_history(handler, path):
    try:
        with _lock:
            last50 = list(_HISTORY[-50:])
        last50.reverse()  # mais recente primeiro
        _send_json(handler, 200, {
            "count":   len(last50),
            "alerts":  last50,
        })
    except Exception as e:
        _send_json(handler, 500, {"error": str(e)})


def handle_alerts_test(handler, path):
    try:
        test_alert = {
            "id":             _make_alert_id(),
            "event_type":     "test",
            "severity":       "N1",
            "title":          "Alerta de Teste NIAS",
            "description":    "Este é um alerta de teste gerado manualmente.",
            "culture":        "soja",
            "region":         "Brasil Central",
            "vfr_brl":        0.0,
            "recommendation": "Nenhuma ação necessária — teste de conectividade.",
            "timestamp":      _now_iso(),
        }
        result = PUSH_ALERTS.dispatch(test_alert)
        _send_json(handler, 200, {
            "ok":     True,
            "alert":  test_alert,
            "result": result,
        })
    except Exception as e:
        _send_json(handler, 500, {"error": str(e)})


def handle_push_alerts(handler, path):
    """Roteador principal para /api/alerts/*"""
    method = handler.command

    if path.startswith("/api/alerts/status"):
        handle_alerts_status(handler, path)
    elif path.startswith("/api/alerts/subscribe") and method == "POST":
        handle_alerts_subscribe(handler, path)
    elif path.startswith("/api/alerts/history"):
        handle_alerts_history(handler, path)
    elif path.startswith("/api/alerts/test") and method == "POST":
        handle_alerts_test(handler, path)
    else:
        _send_json(handler, 404, {"error": "Endpoint não encontrado"})
