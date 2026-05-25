"""Smoke test: endpoints and UI-critical payloads must not fail silently."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 8097
BASE = f"http://127.0.0.1:{PORT}"
ENDPOINTS = [
    "/api/flv/ia/analyze",
    "/api/dashboard/summary",
    "/api/system/audit",
    "/api/ceasa/prices",
    "/api/situation/real",
    "/api/predictx/live",
    "/api/rodovias",
    "/api/produtores",
    "/api/produtores-rj",
    "/api/flv/risk/analyze",
]


def fetch_json(path: str):
    with urllib.request.urlopen(BASE + path, timeout=12) as r:
        assert r.status == 200, (path, r.status)
        raw = r.read().decode("utf-8")
        assert raw.strip(), path
        return json.loads(raw)


def test_endpoints_no_http_error():
    env = os.environ.copy()
    env["PORT"] = str(PORT)
    env["NIAS_DB_PATH"] = str(ROOT / "data" / "nia_flv.db")
    p = subprocess.Popen(["python3", "server.py"], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(1.2)
        for endpoint in ENDPOINTS:
            payload = fetch_json(endpoint)
            assert payload is not None
        dash = fetch_json("/api/dashboard/summary")
        assert dash.get("cards"), "dashboard cards vazio"
        assert dash.get("market") is not None, "market ausente"
        ia = fetch_json("/api/flv/ia/analyze")
        assert ia.get("summary"), "ia summary vazio"
        ceasa = fetch_json("/api/ceasa/prices")
        assert ceasa.get("meta", {}).get("total_records", 0) > 0, "preços CEASA vazios"
    finally:
        p.terminate()
        try:
            p.wait(timeout=3)
        except subprocess.TimeoutExpired:
            p.kill()
