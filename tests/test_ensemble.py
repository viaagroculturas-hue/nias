"""Tests for flv.model.xgb_model and flv.model.ensemble."""
import os
import sys
import math
import unittest
from datetime import datetime, timedelta
from unittest import mock

THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _make_features(n=120, start_price=5.0):
    """Generate synthetic features that XGBoost can actually learn from.

    Shape: same as feature_builder.build_features() output.
    """
    out = []
    base = datetime(2024, 1, 1)
    for i in range(n):
        ds = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        # Price trends slowly up with weekly seasonality.
        y = start_price + 0.01 * i + 0.3 * math.sin(i / 7.0)
        out.append(
            {
                "ds": ds,
                "y": round(y, 3),
                "precip_7d": 20.0 + (i % 5),
                "temp_max_avg": 27.0 + 0.05 * (i % 10),
                "ndvi": 0.55 + 0.01 * ((i % 10) - 5),
                "is_holiday": 0.0,
            }
        )
    return out


class TestXGBModel(unittest.TestCase):
    def test_predict_returns_forecast(self):
        features = _make_features()
        with mock.patch("flv.model.xgb_model.build_features", return_value=features), \
             mock.patch("flv.model.xgb_model.active_macro_regressors", return_value=[]), \
             mock.patch(
                "flv.model.xgb_model.build_future_regressors",
                return_value=[
                    {
                        "ds": (datetime(2024, 1, 1) + timedelta(days=i)).strftime("%Y-%m-%d"),
                        "precip_7d": 20.0,
                        "temp_max_avg": 27.0,
                        "ndvi": 0.55,
                        "is_holiday": 0.0,
                    }
                    for i in range(120, 140)
                ],
            ):
            from flv.model.xgb_model import predict
            result = predict("tomate", "CEAGESP", horizon=15)

        self.assertEqual(result["culture"], "tomate")
        self.assertFalse(result["degraded"])
        self.assertEqual(len(result["forecast"]), 15)
        self.assertIn(result["model"], ("xgb-v1", "gbr-v1"))
        # Forecast prices should be positive and in a plausible range.
        for fc in result["forecast"]:
            self.assertGreater(fc["price"], 0)
            self.assertLess(fc["lower"], fc["price"])
            self.assertGreater(fc["upper"], fc["price"])

    def test_predict_empty_when_insufficient_data(self):
        from flv.model.xgb_model import predict
        with mock.patch("flv.model.xgb_model.build_features", return_value=[]):
            result = predict("tomate", "CEAGESP")
        self.assertEqual(result["forecast"], [])
        self.assertTrue(result["degraded"])
        self.assertEqual(result["model"], "no-data")


class TestEnsembleWeights(unittest.TestCase):
    def test_inverse_mape_weights(self):
        from flv.model.ensemble import _model_weights
        conn = mock.Mock()

        def fake_rolling(c, culture, terminal, days, mv):
            return {"prophet-v1": (6.0, 10), "xgb-v1": (3.0, 10), "gbr-v1": (None, 0)}[mv]

        with mock.patch("flv.model.ensemble.rolling_mape", side_effect=fake_rolling):
            w = _model_weights(conn, "tomate", "CEAGESP")

        # XGB should get ~2x the weight of Prophet (inverse MAPE: 1/3 vs 1/6).
        self.assertAlmostEqual(w["xgb-v1"], 2 * w["prophet-v1"], places=4)
        self.assertAlmostEqual(sum(w.values()), 1.0, places=4)

    def test_default_weights_when_no_history(self):
        from flv.model.ensemble import _model_weights
        conn = mock.Mock()
        with mock.patch("flv.model.ensemble.rolling_mape", return_value=(None, 0)):
            w = _model_weights(conn, "tomate", "CEAGESP")
        self.assertEqual(w["prophet-v1"], 0.5)
        self.assertEqual(w["xgb-v1"], 0.5)


class TestEnsembleBlend(unittest.TestCase):
    def _fake_result(self, model, prices):
        today = datetime(2024, 6, 1)
        fc = [
            {
                "date": (today + timedelta(days=i)).strftime("%Y-%m-%d"),
                "price": p,
                "lower": p * 0.9,
                "upper": p * 1.1,
            }
            for i, p in enumerate(prices, start=1)
        ]
        return {
            "culture": "tomate",
            "model": model,
            "degraded": False,
            "horizon_days": len(prices),
            "trend": "estavel",
            "trend_pct": 0.0,
            "confidence": 70,
            "forecast": fc,
            "historical": [],
            "generated_at": datetime.now().isoformat(),
        }

    def test_blend_50_50(self):
        from flv.model import ensemble
        prophet_res = self._fake_result("prophet-v1", [5.0, 5.2, 5.4])
        xgb_res = self._fake_result("xgb-v1", [4.0, 4.4, 4.8])

        with mock.patch("flv.model.ensemble.prophet_predict", return_value=prophet_res), \
             mock.patch("flv.model.ensemble.xgb_predict", return_value=xgb_res), \
             mock.patch("flv.model.ensemble._model_weights", return_value={"prophet-v1": 0.5, "xgb-v1": 0.5}), \
             mock.patch("flv.db.get_conn", return_value=mock.Mock()):
            ensemble._cache.clear()
            result = ensemble.predict("tomate", "CEAGESP", horizon=3)

        self.assertEqual(result["model"], "ensemble-v1")
        self.assertTrue(result["ensemble"])
        self.assertEqual(len(result["forecast"]), 3)
        self.assertAlmostEqual(result["forecast"][0]["price"], 4.5, places=2)
        self.assertAlmostEqual(result["forecast"][1]["price"], 4.8, places=2)
        self.assertAlmostEqual(result["forecast"][2]["price"], 5.1, places=2)

    def test_blend_weighted(self):
        from flv.model import ensemble
        prophet_res = self._fake_result("prophet-v1", [10.0, 10.0])
        xgb_res = self._fake_result("xgb-v1", [5.0, 5.0])

        with mock.patch("flv.model.ensemble.prophet_predict", return_value=prophet_res), \
             mock.patch("flv.model.ensemble.xgb_predict", return_value=xgb_res), \
             mock.patch("flv.model.ensemble._model_weights", return_value={"prophet-v1": 0.2, "xgb-v1": 0.8}), \
             mock.patch("flv.db.get_conn", return_value=mock.Mock()):
            ensemble._cache.clear()
            result = ensemble.predict("tomate", "CEAGESP", horizon=2)

        # Expected: 0.2 * 10 + 0.8 * 5 = 6.0
        self.assertAlmostEqual(result["forecast"][0]["price"], 6.0, places=2)

    def test_falls_back_when_xgb_degraded(self):
        from flv.model import ensemble
        prophet_res = self._fake_result("prophet-v1", [5.0, 5.2])
        xgb_degraded = {
            "culture": "tomate", "model": "no-data", "degraded": True,
            "horizon_days": 2, "trend": "estavel", "trend_pct": 0, "confidence": 0,
            "forecast": [], "historical": [], "generated_at": datetime.now().isoformat(),
        }
        with mock.patch("flv.model.ensemble.prophet_predict", return_value=prophet_res), \
             mock.patch("flv.model.ensemble.xgb_predict", return_value=xgb_degraded):
            ensemble._cache.clear()
            result = ensemble.predict("tomate", "CEAGESP", horizon=2)

        self.assertEqual(result["model"], "prophet-v1")
        self.assertFalse(result.get("ensemble"))


class TestRetrainCallback(unittest.TestCase):
    def test_register_wires_trainer(self):
        from flv.model import ensemble, retrain_controller
        original = getattr(retrain_controller, "_trainer_cb", None)
        try:
            ensemble.register()
            self.assertIsNotNone(retrain_controller._trainer_cb)
        finally:
            retrain_controller.register_trainer(original)

    def test_clear_cache_selective(self):
        from flv.model import ensemble
        ensemble._cache["tomate_CEAGESP_None_15"] = ({"x": 1}, 123.0)
        ensemble._cache["cebola_CEAGESP_None_15"] = ({"x": 2}, 123.0)
        ensemble.clear_cache("tomate", "CEAGESP")
        self.assertNotIn("tomate_CEAGESP_None_15", ensemble._cache)
        self.assertIn("cebola_CEAGESP_None_15", ensemble._cache)
        # Cleanup.
        ensemble.clear_cache()


if __name__ == "__main__":
    unittest.main()
