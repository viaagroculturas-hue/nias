"""Tests for flv.model.evaluator and flv.model.retrain_controller."""
import os
import sys
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE flv_cultures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name_pt TEXT
        );
        CREATE TABLE flv_ceasa_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            culture_id INTEGER NOT NULL,
            terminal TEXT,
            price_date TEXT NOT NULL,
            price_avg REAL,
            price_min REAL,
            price_max REAL,
            source TEXT
        );
        CREATE TABLE flv_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            culture_id INTEGER NOT NULL,
            mun_id INTEGER,
            terminal TEXT,
            generated_at TEXT DEFAULT (datetime('now')),
            target_date TEXT NOT NULL,
            horizon_days INTEGER,
            predicted_price REAL NOT NULL,
            price_lower_80 REAL,
            price_upper_80 REAL,
            trend_direction TEXT,
            confidence_pct REAL,
            model_version TEXT DEFAULT 'prophet-v1',
            features_json TEXT
        );
        CREATE TABLE flv_accuracy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prediction_id INTEGER,
            actual_price REAL NOT NULL,
            actual_date TEXT NOT NULL,
            mape_pct REAL,
            evaluated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE flv_model_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            culture_slug TEXT NOT NULL,
            terminal TEXT,
            model_version TEXT,
            started_at TEXT DEFAULT (datetime('now')),
            finished_at TEXT,
            mape_before REAL,
            mape_after REAL,
            trigger_reason TEXT,
            status TEXT,
            notes TEXT
        );
        INSERT INTO flv_cultures (slug, name_pt) VALUES ('tomate', 'Tomate');
        """
    )
    conn.commit()
    return path, conn


def _seed_prediction(conn, target_date, predicted, model="prophet-v1", culture="tomate", terminal="CEAGESP"):
    cid = conn.execute("SELECT id FROM flv_cultures WHERE slug=?", (culture,)).fetchone()["id"]
    cur = conn.execute(
        "INSERT INTO flv_predictions (culture_id, terminal, target_date, horizon_days, predicted_price, model_version) "
        "VALUES (?,?,?,?,?,?)",
        (cid, terminal, target_date, 7, predicted, model),
    )
    return cur.lastrowid


def _seed_actual(conn, date, price, culture="tomate", terminal="CEAGESP"):
    cid = conn.execute("SELECT id FROM flv_cultures WHERE slug=?", (culture,)).fetchone()["id"]
    conn.execute(
        "INSERT INTO flv_ceasa_prices (culture_id, terminal, price_date, price_avg) VALUES (?,?,?,?)",
        (cid, terminal, date, price),
    )


class TestEvaluator(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _today(self):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _days_ago(self, n):
        return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")

    def test_evaluate_exact_match(self):
        from flv.model.evaluator import evaluate_predictions
        d = self._days_ago(2)
        pid = _seed_prediction(self.conn, d, predicted=5.00)
        _seed_actual(self.conn, d, price=4.00)
        self.conn.commit()

        n = evaluate_predictions(self.conn)
        self.assertEqual(n, 1)
        row = self.conn.execute("SELECT * FROM flv_accuracy WHERE prediction_id=?", (pid,)).fetchone()
        self.assertIsNotNone(row)
        self.assertAlmostEqual(row["actual_price"], 4.00)
        # MAPE = |5 - 4| / 4 * 100 = 25%
        self.assertAlmostEqual(row["mape_pct"], 25.0, places=2)

    def test_evaluate_uses_nearest_earlier_price(self):
        """When target_date has no price (weekend/holiday), fall back to closest earlier date <= 3d."""
        from flv.model.evaluator import evaluate_predictions
        target = self._days_ago(1)
        pid = _seed_prediction(self.conn, target, predicted=5.10)
        # Observed 2 days earlier only
        _seed_actual(self.conn, self._days_ago(3), price=5.00)
        self.conn.commit()

        n = evaluate_predictions(self.conn)
        self.assertEqual(n, 1)
        row = self.conn.execute("SELECT * FROM flv_accuracy WHERE prediction_id=?", (pid,)).fetchone()
        self.assertAlmostEqual(row["actual_price"], 5.00)
        self.assertEqual(row["actual_date"], self._days_ago(3))

    def test_evaluate_skips_when_no_price(self):
        from flv.model.evaluator import evaluate_predictions
        _seed_prediction(self.conn, self._days_ago(1), predicted=5.10)
        self.conn.commit()
        n = evaluate_predictions(self.conn)
        self.assertEqual(n, 0)

    def test_evaluate_is_idempotent(self):
        from flv.model.evaluator import evaluate_predictions
        d = self._days_ago(2)
        _seed_prediction(self.conn, d, predicted=5.00)
        _seed_actual(self.conn, d, price=4.00)
        self.conn.commit()
        n1 = evaluate_predictions(self.conn)
        n2 = evaluate_predictions(self.conn)
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 0)
        c = self.conn.execute("SELECT COUNT(*) AS c FROM flv_accuracy").fetchone()
        self.assertEqual(c["c"], 1)

    def test_evaluate_skips_future_predictions(self):
        from flv.model.evaluator import evaluate_predictions
        future = (datetime.now(timezone.utc) + timedelta(days=5)).strftime("%Y-%m-%d")
        _seed_prediction(self.conn, future, predicted=5.00)
        self.conn.commit()
        n = evaluate_predictions(self.conn)
        self.assertEqual(n, 0)

    def test_rolling_mape(self):
        from flv.model.evaluator import evaluate_predictions, rolling_mape
        for days_ago, predicted in [(5, 5.10), (10, 5.20), (20, 4.80), (35, 6.00)]:
            d = self._days_ago(days_ago)
            _seed_prediction(self.conn, d, predicted=predicted)
            _seed_actual(self.conn, d, price=5.00)
        self.conn.commit()
        evaluate_predictions(self.conn)

        m30, n30 = rolling_mape(self.conn, "tomate", "CEAGESP", 30, "prophet-v1")
        self.assertEqual(n30, 3)  # 35-day old one excluded
        m_all, _ = rolling_mape(self.conn, "tomate", "CEAGESP", 365, "prophet-v1")
        self.assertIsNotNone(m_all)

    def test_summary_shape(self):
        from flv.model.evaluator import evaluate_predictions, summary
        d = self._days_ago(2)
        _seed_prediction(self.conn, d, predicted=5.00)
        _seed_actual(self.conn, d, price=4.00)
        self.conn.commit()
        evaluate_predictions(self.conn)

        s = summary(self.conn)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["culture"], "tomate")
        self.assertEqual(s[0]["terminal"], "CEAGESP")
        self.assertEqual(s[0]["model_version"], "prophet-v1")
        self.assertIsNotNone(s[0]["mape_30d"])


class TestRetrainController(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _days_ago(self, n):
        return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")

    def _seed_evaluated(self, days_ago, mape):
        """Insert a prediction + evaluated accuracy row with a controlled MAPE."""
        d = self._days_ago(days_ago)
        pid = _seed_prediction(self.conn, d, predicted=5.00)
        self.conn.execute(
            "INSERT INTO flv_accuracy (prediction_id, actual_price, actual_date, mape_pct) VALUES (?,?,?,?)",
            (pid, 5.00, d, mape),
        )

    def test_no_trigger_when_mape_below_threshold(self):
        from flv.model.retrain_controller import check_triggers
        for days in range(1, 10):
            self._seed_evaluated(days, mape=5.0)
        self.conn.commit()
        self.assertEqual(check_triggers(self.conn), [])

    def test_trigger_when_mape_exceeds_threshold(self):
        from flv.model.retrain_controller import check_triggers
        for days in range(1, 10):
            self._seed_evaluated(days, mape=15.0)  # above 12% default
        self.conn.commit()
        t = check_triggers(self.conn)
        self.assertEqual(len(t), 1)
        self.assertEqual(t[0]["culture_slug"], "tomate")
        self.assertGreater(t[0]["mape_30d"], 12.0)
        self.assertIn("threshold", t[0]["reason"])

    def test_trigger_when_relative_degradation(self):
        """Prior 30d window averaged 5% MAPE; new 30d at 8%. 8/5 = 1.6 > 1.3 → should trigger."""
        from flv.model.retrain_controller import check_triggers
        # Recent window: days_ago 1..29
        for days in range(1, 30):
            self._seed_evaluated(days, mape=8.0)
        # Prior window: days_ago 31..59
        for days in range(31, 60):
            self._seed_evaluated(days, mape=5.0)
        self.conn.commit()
        t = check_triggers(self.conn)
        self.assertEqual(len(t), 1)
        self.assertIn("prior", t[0]["reason"])

    def test_skip_when_insufficient_samples(self):
        from flv.model.retrain_controller import check_triggers
        # Only 2 samples — below MIN_SAMPLES=5
        self._seed_evaluated(3, mape=25.0)
        self._seed_evaluated(5, mape=30.0)
        self.conn.commit()
        self.assertEqual(check_triggers(self.conn), [])

    def test_run_logs_deferred_without_trainer(self):
        from flv.model.retrain_controller import run
        for days in range(1, 10):
            self._seed_evaluated(days, mape=20.0)
        self.conn.commit()
        res = run(self.conn)
        self.assertEqual(len(res["triggers"]), 1)
        self.assertEqual(res["actions"][0]["status"], "deferred")
        row = self.conn.execute("SELECT status FROM flv_model_runs").fetchone()
        self.assertEqual(row["status"], "deferred")

    def test_run_calls_registered_trainer(self):
        from flv.model import retrain_controller
        for days in range(1, 10):
            self._seed_evaluated(days, mape=20.0)
        self.conn.commit()

        trainer = mock.Mock(return_value=(True, 8.5))
        retrain_controller.register_trainer(trainer)
        try:
            res = retrain_controller.run(self.conn)
        finally:
            retrain_controller.register_trainer(None)

        trainer.assert_called_once()
        self.assertEqual(res["actions"][0]["status"], "completed")
        self.assertEqual(res["actions"][0]["mape_after"], 8.5)


if __name__ == "__main__":
    unittest.main()
