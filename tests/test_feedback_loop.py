import sqlite3
import unittest

from learning.feedback_loop import FeedbackLoop, init_feedback_schema


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE flv_cultures (
            id INTEGER PRIMARY KEY,
            slug TEXT,
            name_pt TEXT
        );
        CREATE TABLE flv_predictions (
            id INTEGER PRIMARY KEY,
            culture_id INTEGER,
            terminal TEXT,
            generated_at TEXT DEFAULT (datetime('now')),
            target_date TEXT,
            predicted_price REAL,
            model_version TEXT
        );
        CREATE TABLE flv_ceasa_prices (
            id INTEGER PRIMARY KEY,
            culture_id INTEGER,
            terminal TEXT,
            price_date TEXT,
            price_avg REAL,
            source TEXT
        );
        CREATE TABLE flv_accuracy (
            id INTEGER PRIMARY KEY,
            prediction_id INTEGER,
            actual_price REAL,
            actual_date TEXT,
            mape_pct REAL
        );
        CREATE TABLE flv_climate (
            obs_date TEXT,
            precip_mm REAL,
            temp_max_c REAL
        );
        CREATE TABLE flv_macro_indicators (
            obs_date TEXT,
            diesel_change_pct REAL,
            brent_change_pct REAL,
            wti_change_pct REAL
        );
        """
    )
    init_feedback_schema(conn)
    conn.execute("INSERT INTO flv_cultures (id, slug, name_pt) VALUES (1, 'tomate', 'Tomate')")
    return conn


def _insert_pair(conn, predicted, actual, target_date="2026-04-28"):
    conn.execute(
        """
        INSERT INTO flv_predictions
            (id, culture_id, terminal, target_date, predicted_price, model_version)
        VALUES (10, 1, 'CEAGESP', ?, ?, 'test-model')
        """,
        (target_date, predicted),
    )
    conn.execute(
        """
        INSERT INTO flv_ceasa_prices
            (culture_id, terminal, price_date, price_avg, source)
        VALUES (1, 'CEAGESP', ?, ?, 'CEPEA/ESALQ')
        """,
        (target_date, actual),
    )


class FeedbackLoopTest(unittest.TestCase):
    def test_no_adjustment_when_error_is_within_threshold(self):
        conn = _conn()
        _insert_pair(conn, predicted=100.0, actual=104.0)

        result = FeedbackLoop(conn=conn).run_daily(reference_date="2026-04-28")

        self.assertEqual(result["evaluated"], 1)
        self.assertEqual(result["adjustments_count"], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM flv_accuracy").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM inteligencia_evolucao_log").fetchone()[0], 0)

    def test_adjusts_weights_and_logs_intelligence_evolution(self):
        conn = _conn()
        _insert_pair(conn, predicted=90.0, actual=100.0)
        conn.execute("INSERT INTO flv_climate VALUES ('2026-04-28', 30.0, 38.0)")
        conn.execute("INSERT INTO flv_macro_indicators VALUES ('2026-04-28', 1.0, 1.0, 0.0)")

        result = FeedbackLoop(conn=conn).run_daily(reference_date="2026-04-28")

        self.assertEqual(result["adjustments_count"], 1)

        weights = conn.execute(
            "SELECT climate_weight, logistics_weight FROM learning_model_weights"
        ).fetchone()
        self.assertIsNotNone(weights)
        self.assertGreater(weights["climate_weight"], 0.5)
        self.assertEqual(round(weights["climate_weight"] + weights["logistics_weight"], 4), 1.0)

        log = conn.execute("SELECT * FROM inteligencia_evolucao_log").fetchone()
        self.assertEqual(log["event_type"], "ajuste_pesos")
        self.assertEqual(log["prediction_id"], 10)
        self.assertEqual(log["error_pct"], 10.0)
        self.assertIn("Previsao subestimou", log["adjustment_reason"])


if __name__ == "__main__":
    unittest.main()

