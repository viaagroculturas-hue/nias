import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch


class RiskIntelligenceTest(unittest.TestCase):
    def test_news_risk_scores_requested_triggers(self):
        from flv.collectors.news_risk import _score_text

        cases = [
            ("Greve de Caminhoneiros bloqueia corredores de abastecimento", "GREVE_CAMINHONEIROS"),
            ("Guerra na Ucrânia volta a pressionar fertilizantes", "GUERRA_UCRANIA"),
            ("Seca no Canal do Panamá reduz trânsito de navios", "SECA_CANAL_PANAMA"),
        ]

        for text, expected_tag in cases:
            score, tags = _score_text(text)
            self.assertGreaterEqual(score, 0.9)
            self.assertIn(expected_tag, tags)

    def test_latest_news_and_teleconnections_are_injected_into_last_feature(self):
        from flv.model import feature_builder

        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        class FakeRow(dict):
            def __getitem__(self, key):
                return self.get(key)

        class FakeCursor:
            def __init__(self, rows):
                self.rows = rows

            def fetchone(self):
                return self.rows[0] if self.rows else None

            def fetchall(self):
                return self.rows

        class FakeConn:
            def execute(self, sql, params=()):
                if "SELECT id FROM flv_cultures" in sql:
                    return FakeCursor([FakeRow(id=1)])
                if "FROM flv_ceasa_prices" in sql:
                    return FakeCursor([FakeRow(ds=yesterday, y=85.0)])
                if "FROM flv_climate" in sql:
                    return FakeCursor([])
                if "FROM flv_ndvi" in sql:
                    return FakeCursor([])
                if "FROM flv_macro_indicators" in sql:
                    return FakeCursor([])
                if "FROM flv_news_risk_daily" in sql and "WHERE obs_date >= ?" in sql:
                    return FakeCursor([])
                if "FROM flv_news_risk_daily" in sql:
                    return FakeCursor([
                        FakeRow(
                            obs_date=today,
                            risk_index=0.92,
                            top_tags_json=json.dumps([["GREVE_CAMINHONEIROS", 1]]),
                            sources_json=json.dumps(["Reuters"]),
                        )
                    ])
                if "FROM flv_news_events" in sql:
                    return FakeCursor([
                        FakeRow(
                            obs_ts=f"{today}T00:00:00+00:00",
                            source="Reuters",
                            title="Greve de Caminhoneiros afeta frete",
                            url="https://example.com",
                            risk_score=1.0,
                            tags_json=json.dumps(["GREVE_CAMINHONEIROS"]),
                        )
                    ])
                if "FROM flv_global_climate" in sql and "WHERE obs_date >= ?" in sql:
                    return FakeCursor([])
                if "FROM flv_global_climate" in sql:
                    return FakeCursor([
                        FakeRow(obs_date=today, oni=1.1, atl_north_warm_idx=0.6, source="NOAA/CPC ONI")
                    ])
                return FakeCursor([])

        with patch("flv.db.get_conn", return_value=FakeConn()):
            rows = feature_builder.build_features("tomate", terminal="CEAGESP", days=1)

        self.assertEqual(rows[-1]["news_risk_index"], 0.92)
        self.assertEqual(rows[-1]["news_top_tags"], [["GREVE_CAMINHONEIROS", 1]])
        self.assertEqual(rows[-1]["news_sources"], ["Reuters"])
        self.assertEqual(rows[-1]["news_events"][0]["title"], "Greve de Caminhoneiros afeta frete")
        self.assertEqual(rows[-1]["oni"], 1.1)
        self.assertEqual(rows[-1]["atl_north_warm_idx"], 0.6)


if __name__ == "__main__":
    unittest.main()
