import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

from core.market_predictor import HORIZON_DAYS, MarketPredictor, predict_market_trends


class MarketPredictorTest(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()
        self._seed_data()

    def tearDown(self):
        self.conn.close()
        os.remove(self.db_path)

    def _create_schema(self):
        self.conn.executescript(
            """
            CREATE TABLE flv_cultures (
                id INTEGER PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                name_pt TEXT,
                unit TEXT,
                main_producers TEXT
            );
            CREATE TABLE flv_ceasa_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                culture_id INTEGER NOT NULL,
                terminal TEXT,
                price_date TEXT NOT NULL,
                price_avg REAL NOT NULL,
                source TEXT
            );
            CREATE TABLE flv_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                culture_id INTEGER,
                region_key TEXT,
                alert_type TEXT,
                severity TEXT,
                trigger_value REAL,
                threshold_value REAL,
                impact_supply_pct REAL,
                impact_price_pct REAL,
                message TEXT,
                valid_until TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE flv_municipalities (
                id INTEGER PRIMARY KEY,
                ibge_code TEXT,
                name TEXT,
                state_uf TEXT
            );
            CREATE TABLE flv_mun_culture (
                mun_id INTEGER,
                culture_id INTEGER
            );
            CREATE TABLE flv_ndvi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mun_id INTEGER,
                obs_date TEXT,
                ndvi_value REAL,
                ndvi_anomaly REAL
            );
            CREATE TABLE flv_climate (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mun_id INTEGER,
                obs_date TEXT,
                temp_max_c REAL,
                temp_min_c REAL,
                precip_mm REAL
            );
            CREATE TABLE flv_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                culture_id INTEGER,
                target_date TEXT,
                horizon_days INTEGER,
                predicted_price REAL,
                price_lower_80 REAL,
                price_upper_80 REAL,
                trend_direction TEXT,
                confidence_pct REAL,
                model_version TEXT,
                features_json TEXT
            );
            """
        )
        self.conn.commit()

    def _seed_data(self):
        self.conn.executemany(
            "INSERT INTO flv_cultures (id, slug, name_pt, unit, main_producers) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "tomate", "Tomate Mesa", "R$/cx", "GO,SP,MG"),
                (2, "cebola", "Cebola", "R$/sc", "SC,BA,SP,GO"),
                (3, "batata", "Batata Inglesa", "R$/sc", "MG,SP,PR,BA"),
            ],
        )
        self.conn.execute(
            "INSERT INTO flv_municipalities (id, ibge_code, name, state_uf) VALUES (10, '5206206', 'Cristalina', 'GO')"
        )
        self.conn.execute("INSERT INTO flv_mun_culture (mun_id, culture_id) VALUES (10, 1)")

        start = datetime.now() - timedelta(days=39)
        for idx in range(40):
            price_date = (start + timedelta(days=idx)).strftime("%Y-%m-%d")
            self.conn.execute(
                """
                INSERT INTO flv_ceasa_prices (culture_id, terminal, price_date, price_avg, source)
                VALUES (1, 'CEPEA', ?, ?, 'CEPEA/ESALQ')
                """,
                (price_date, 50.0 + idx * 0.05),
            )

        today = datetime.now().strftime("%Y-%m-%d")
        for days_ago in range(7):
            obs_date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            self.conn.execute(
                "INSERT INTO flv_climate (mun_id, obs_date, temp_max_c, temp_min_c, precip_mm) VALUES (10, ?, 37.0, 19.0, 0.2)",
                (obs_date,),
            )
        self.conn.execute(
            "INSERT INTO flv_ndvi (mun_id, obs_date, ndvi_value, ndvi_anomaly) VALUES (10, ?, 0.42, -0.12)",
            (today,),
        )
        self.conn.execute(
            """
            INSERT INTO flv_alerts (
                culture_id, region_key, alert_type, severity, trigger_value,
                threshold_value, impact_supply_pct, impact_price_pct, message, valid_until
            )
            VALUES (1, 'cristalina_go', 'seca', 'vermelho', 1.4, 3.0, -35.0, 45.0,
                    'Seca em Cristalina-GO com quebra de safra de tomate', date('now', '+15 days'))
            """
        )
        self.conn.commit()

    def test_predicts_shortage_alert_from_bio_climate_break(self):
        prediction = MarketPredictor(self.db_path).predict("tomate")

        self.assertEqual(prediction.horizon_days, HORIZON_DAYS)
        self.assertEqual(prediction.trend, "alta")
        self.assertGreater(prediction.predicted_price, prediction.current_price)
        self.assertEqual(len(prediction.forecast), HORIZON_DAYS)
        self.assertGreaterEqual(prediction.bio_climate.climate_risk_score, 70)
        self.assertTrue(any(alert["type"] == "Escassez Iminente" for alert in prediction.alerts))

    def test_public_api_returns_supported_products_with_fallbacks(self):
        report = predict_market_trends(db_path=self.db_path)

        self.assertEqual(set(report["products"]), {"tomate", "cebola", "batata"})
        self.assertEqual(report["horizon_days"], HORIZON_DAYS)
        self.assertIn("summary", report)
        for product in report["products"].values():
            self.assertEqual(len(product["forecast"]), HORIZON_DAYS)

    def test_persist_stores_predictions_and_shortage_alert(self):
        prediction = MarketPredictor(self.db_path).predict("tomate", persist=True)

        pred_count = self.conn.execute("SELECT COUNT(*) FROM flv_predictions").fetchone()[0]
        shortage_count = self.conn.execute(
            "SELECT COUNT(*) FROM flv_alerts WHERE alert_type = 'Escassez Iminente'"
        ).fetchone()[0]

        self.assertEqual(pred_count, HORIZON_DAYS)
        self.assertTrue(prediction.alerts)
        self.assertEqual(shortage_count, 1)


if __name__ == "__main__":
    unittest.main()
