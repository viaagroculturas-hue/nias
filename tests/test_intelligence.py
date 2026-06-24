"""Testes do Motor de Inteligência NIA$ e endpoint /api/health.
Rodar com servidor ativo: python tests/test_intelligence.py
"""
from __future__ import annotations
import json, os, sys, urllib.request, urllib.error

BASE = os.getenv("NIAS_BASE_URL", "http://127.0.0.1:8080").rstrip("/")

def fetch(path: str) -> tuple[int, dict | None]:
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "NIAS-test/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8")
            return r.status, json.loads(body)
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:
        return 0, None

def test_health():
    code, data = fetch("/api/health")
    assert code == 200, f"/api/health retornou {code}"
    assert data['status'] == 'ok', f"status != ok: {data}"
    assert data['service'] == 'NIAS'
    assert data['version'] == '3.0'
    assert 'modules' in data
    assert data['modules']['server'] == 'ok'
    print("  [OK] /api/health")

def test_intelligence_status():
    code, data = fetch("/api/intelligence/")
    assert code == 200, f"/api/intelligence retornou {code}"
    assert data['status'] == 'active'
    assert 'capabilities' in data
    print("  [OK] /api/intelligence/")

def test_opportunities():
    code, data = fetch("/api/intelligence/opportunities")
    assert code == 200, f"/api/intelligence/opportunities retornou {code}"
    assert 'opportunities' in data
    opps = data['opportunities']
    if opps:
        opp = opps[0]
        assert 'produto' in opp
        assert 'score' in opp
        assert 0 <= opp['score'] <= 100
        assert 'motivos' in opp
        assert 'acao_recomendada' in opp
        assert 'fontes' in opp
        assert 'confianca' in opp
        print(f"  [OK] /api/intelligence/opportunities ({len(opps)} produtos)")
    else:
        print("  [OK] /api/intelligence/opportunities (sem dados no DB — estrutura ok)")

def test_predictions():
    code, data = fetch("/api/intelligence/predictions")
    assert code == 200, f"/api/intelligence/predictions retornou {code}"
    assert 'predictions' in data
    preds = data['predictions']
    if preds:
        p = preds[0]
        assert 'produto' in p
        assert 'tendencia' in p
        assert p['tendencia'] in ('alta', 'queda', 'estabilidade', 'incerto')
        assert 'explicacao' in p
        assert len(p['explicacao']) > 20, "Explicação muito curta"
        assert 'confianca' in p
        assert 'fontes' in p
        print(f"  [OK] /api/intelligence/predictions ({len(preds)} previsões)")
    else:
        print("  [OK] /api/intelligence/predictions (sem dados — estrutura ok)")

def test_alerts():
    code, data = fetch("/api/intelligence/alerts")
    assert code == 200, f"/api/intelligence/alerts retornou {code}"
    assert 'alerts' in data
    alerts = data['alerts']
    if alerts:
        a = alerts[0]
        assert 'titulo' in a
        assert 'prioridade' in a
        assert 'explicacao' in a
        assert 'acao_recomendada' in a
        print(f"  [OK] /api/intelligence/alerts ({len(alerts)} alertas)")
    else:
        print("  [OK] /api/intelligence/alerts (sem alertas ativos)")

def test_report():
    code, data = fetch("/api/intelligence/report")
    assert code == 200, f"/api/intelligence/report retornou {code}"
    assert 'resumo' in data
    assert 'oportunidades' in data
    assert 'riscos' in data
    assert 'tendencias' in data
    assert 'acoes_recomendadas' in data
    assert 'confianca_geral' in data
    assert data['confianca_geral'] in ('alta', 'media', 'baixa')
    print(f"  [OK] /api/intelligence/report (confiança: {data['confianca_geral']})")

def test_memory():
    code, data = fetch("/api/intelligence/memory")
    assert code == 200, f"/api/intelligence/memory retornou {code}"
    assert 'accuracy' in data
    assert 'total_verificados' in data['accuracy']
    print(f"  [OK] /api/intelligence/memory (verificados: {data['accuracy']['total_verificados']})")

def main():
    print("=" * 60)
    print("TESTE: Motor de Inteligência NIA$ + Health Check")
    print("=" * 60)

    tests = [
        test_health,
        test_intelligence_status,
        test_opportunities,
        test_predictions,
        test_alerts,
        test_report,
        test_memory,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except AssertionError as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  [ERROR] {t.__name__}: {e}")
            failed += 1

    print(f"\nResultado: {passed}/{len(tests)} passed, {failed} failed")
    return 1 if failed else 0

if __name__ == "__main__":
    raise SystemExit(main())
