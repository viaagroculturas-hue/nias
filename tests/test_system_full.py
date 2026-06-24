"""Auditoria funcional NIAS: endpoints, abas, comandos e mapas.
Executar com servidor local ativo: NIAS_BASE_URL=http://127.0.0.1:8080 python tests/test_system_full.py
"""
from __future__ import annotations
import json, os, re, sys, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = os.getenv("NIAS_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
ENDPOINTS = [
    "/", "/api/dashboard/summary", "/api/flv/ia/analyze", "/api/system/audit",
    "/api/system/sources", "/api/ceasa/prices", "/api/situation/real",
    "/api/predictx/live", "/api/flv/risk/analyze", "/api/flv/risk/sources",
    "/api/flv/cultures", "/api/flv/prices", "/api/flv/alerts", "/api/flv/heatmap",
    "/api/ceasas", "/api/produtores", "/api/rodovias", "/api/warroom/status",
    "/api/crisis/events", "/api/growth/scores", "/api/distributors", "/api/news",
    "/api/reports", "/api/autonomous/status", "/api/predictix/intel",
]

def fetch(path: str) -> tuple[int, bytes]:
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "NIAS-full-test/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=7) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

def test_index_structure() -> list[str]:
    html = (ROOT / "index.html").read_text(encoding="utf-8", errors="ignore")
    errors = []
    nav_ids = sorted(set(re.findall(r"showPanel\('([^']+)'\)", html)))
    panels = set(re.findall(r'id="panel-([^"\s]+)"', html))
    missing = [x for x in nav_ids if x not in panels]
    if missing:
        errors.append("Botões sem painel correspondente: " + ", ".join(missing))
    for required in ["map", "map-municipal", "pxx-map"]:
        if f'id="{required}"' not in html:
            errors.append(f"Container de mapa ausente: {required}")
    for fn in ["addLocalAdminFallback", "addCountryContours", "addStateContours", "initMap", "initMunicipal"]:
        if f"function {fn}" not in html:
            errors.append(f"Função de mapa ausente: {fn}")
    return errors

def main() -> int:
    failures = []
    for ep in ENDPOINTS:
        code, body = fetch(ep)
        if code != 200:
            failures.append(f"{ep}: HTTP {code} {body[:160]!r}")
        elif ep != "/":
            try:
                json.loads(body.decode("utf-8"))
            except Exception as exc:
                failures.append(f"{ep}: resposta não JSON ({exc})")
    failures.extend(test_index_structure())
    if failures:
        print("FALHAS:")
        for f in failures:
            print("-", f)
        return 1
    print(f"OK: {len(ENDPOINTS)} endpoints + estrutura de abas/mapas validados.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
