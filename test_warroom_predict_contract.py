from unittest.mock import patch

from flv.api import routes
from flv.arquitetura_sulamericana import construir_grafo_sulamericano


def test_south_american_edges_include_financial_flow():
    graph = construir_grafo_sulamericano()

    assert graph["edges"]
    assert all("fluxo_financeiro" in edge for edge in graph["edges"])
    assert all(edge["fluxo_financeiro"] >= 0 for edge in graph["edges"])


def test_predict_dossier_uses_predict_report_and_premium_triggers():
    predict_payload = {
        "culture": "soja",
        "model": "ets-fallback",
        "trend": "alta",
        "trend_pct": 2.8,
        "confidence": 61,
        "forecast": [{"date": "2026-04-30", "price": 123.45}],
        "report": "Relatório com Reuters/Bloomberg anexado.",
    }
    triggers = [
        {
            "source": "Reuters",
            "category": "commodities",
            "title": "Soja sobe com demanda chinesa",
            "published_at": "2026-04-29 00:00:00",
            "sentiment": "positivo",
            "sentiment_score": 0.75,
            "relevance_score": 0.9,
        }
    ]

    with patch("flv.db.query", return_value=[]) as query_mock, patch(
        "flv.model.prophet_model.predict", return_value=predict_payload
    ) as predict_mock, patch("flv.model.explainer.coletar_gatilhos_premium", return_value=triggers):
        dossier = routes._get_predict_dossier("soja", {"terminal": "CEAGESP", "horizon": "7"})

    predict_mock.assert_called_once_with("soja", "CEAGESP", horizon=7)
    query_mock.assert_called_once()
    assert list(dossier["windows"].keys()) == ["midia", "feed_premium", "predictix"]
    assert dossier["windows"]["predictix"]["report"] == predict_payload["report"]
    assert dossier["windows"]["feed_premium"]["items"][0]["source"] == "Reuters"
