"""Tests for flv.collectors.macro and feature_builder macro integration.

These tests stub the network layer so they don't hit BCB/ANP during CI.
"""
import os
import sys
import sqlite3
import tempfile
import unittest
from unittest import mock

THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _fresh_db():
    """Spin up an isolated SQLite file with the flv_macro + minimal tables the tests touch."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE flv_macro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series TEXT NOT NULL,
            obs_date TEXT NOT NULL,
            value REAL NOT NULL,
            source TEXT NOT NULL DEFAULT 'BCB',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(series, obs_date)
        );
        CREATE TABLE flv_cultures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL
        );
        CREATE TABLE flv_ceasa_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            culture_id INTEGER NOT NULL,
            terminal TEXT,
            price_date TEXT NOT NULL,
            price_avg REAL NOT NULL
        );
        CREATE TABLE flv_climate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER,
            obs_date TEXT,
            temp_max_c REAL,
            precip_mm REAL
        );
        CREATE TABLE flv_ndvi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER,
            obs_date TEXT,
            ndvi_value REAL
        );
        """
    )
    conn.commit()
    return path, conn


class TestMacroCollector(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _patch_db(self):
        """Make flv.db.get_conn return our isolated connection."""
        from flv import db as db_mod
        return mock.patch.object(db_mod, "get_conn", lambda: self.conn)

    def test_br_to_iso(self):
        from flv.collectors.macro import _br_to_iso
        self.assertEqual(_br_to_iso("01/03/2026"), "2026-03-01")
        self.assertIsNone(_br_to_iso(""))
        self.assertIsNone(_br_to_iso("2026-01-01"))

    def test_fetch_bcb_upserts_series(self):
        from flv.collectors import macro

        fake_json = [
            {"data": "01/03/2026", "valor": "5.10"},
            {"data": "02/03/2026", "valor": "5.15"},
        ]
        with mock.patch.object(macro, "_http_get_json", return_value=fake_json):
            inserted = macro.fetch_bcb(self.conn, lookback_days=10)

        # 3 series x 2 rows = 6
        self.assertEqual(inserted, 6)
        rows = self.conn.execute(
            "SELECT series, obs_date, value FROM flv_macro ORDER BY series, obs_date"
        ).fetchall()
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0]["obs_date"], "2026-03-01")

        # Upsert idempotency
        with mock.patch.object(macro, "_http_get_json", return_value=fake_json):
            macro.fetch_bcb(self.conn, lookback_days=10)
        rows2 = self.conn.execute("SELECT COUNT(*) AS c FROM flv_macro").fetchone()
        self.assertEqual(rows2["c"], 6)

    def test_fetch_bcb_skips_malformed(self):
        from flv.collectors import macro

        fake_json = [
            {"data": "bad", "valor": "5.10"},
            {"data": "01/03/2026", "valor": None},
            {"data": "02/03/2026", "valor": "x"},
            {"data": "03/03/2026", "valor": "4.99"},
        ]
        with mock.patch.object(macro, "_http_get_json", return_value=fake_json):
            inserted = macro.fetch_bcb(self.conn)
        # Only 1 valid row per series × 3 series
        self.assertEqual(inserted, 3)

    def test_diesel_parser_picks_s10(self):
        from flv.collectors import macro

        html = b"<html>stuff DIESEL S10   6,489 other</html>"

        class FakeResp:
            def __init__(self, data): self._data = data
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return self._data

        with mock.patch.object(macro.urllib.request, "urlopen", return_value=FakeResp(html)):
            inserted = macro.fetch_diesel_anp(self.conn)
        self.assertEqual(inserted, 1)
        row = self.conn.execute(
            "SELECT series, value FROM flv_macro WHERE series='diesel_s10'"
        ).fetchone()
        self.assertAlmostEqual(row["value"], 6.489, places=3)

    def test_diesel_graceful_when_unavailable(self):
        from flv.collectors import macro

        with mock.patch.object(
            macro.urllib.request, "urlopen",
            side_effect=Exception("boom"),
        ):
            inserted = macro.fetch_diesel_anp(self.conn)
        self.assertEqual(inserted, 0)

    def test_series_as_map(self):
        from flv.collectors import macro
        self.conn.execute(
            "INSERT INTO flv_macro (series, obs_date, value, source) VALUES ('usd_brl', '2026-03-01', 5.10, 'BCB')"
        )
        self.conn.execute(
            "INSERT INTO flv_macro (series, obs_date, value, source) VALUES ('usd_brl', '2026-03-02', 5.15, 'BCB')"
        )
        self.conn.commit()
        m = macro.series_as_map(self.conn, "usd_brl", "2026-03-01")
        self.assertEqual(m, {"2026-03-01": 5.10, "2026-03-02": 5.15})


class TestFeatureBuilderMacro(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()
        # Seed a culture + 3 price observations
        self.conn.execute("INSERT INTO flv_cultures (slug) VALUES ('tomate')")
        cid = self.conn.execute("SELECT id FROM flv_cultures WHERE slug='tomate'").fetchone()["id"]
        for i, (d, p) in enumerate([
            ("2026-03-01", 6.20),
            ("2026-03-02", 6.30),
            ("2026-03-03", 6.10),
        ]):
            self.conn.execute(
                "INSERT INTO flv_ceasa_prices (culture_id, terminal, price_date, price_avg) VALUES (?,?,?,?)",
                (cid, "CEAGESP", d, p),
            )
        # Seed macro: usd_brl has all 3 dates; diesel only has 1 (before start → forward-fill)
        for d, v in [("2026-03-01", 5.00), ("2026-03-02", 5.05), ("2026-03-03", 5.10)]:
            self.conn.execute(
                "INSERT INTO flv_macro (series, obs_date, value, source) VALUES ('usd_brl',?,?,'BCB')",
                (d, v),
            )
        self.conn.execute(
            "INSERT INTO flv_macro (series, obs_date, value, source) VALUES ('diesel_s10','2026-02-25',6.30,'ANP')"
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def test_build_features_attaches_macro(self):
        from flv import db as db_mod
        with mock.patch.object(db_mod, "get_conn", lambda: self.conn):
            # Also need to stub thresholds holidays import — already lazy-loaded in builder
            from flv.model.feature_builder import build_features, active_macro_regressors
            feats = build_features("tomate", terminal="CEAGESP")

        self.assertEqual(len(feats), 3)
        self.assertAlmostEqual(feats[0]["usd_brl"], 5.00)
        self.assertAlmostEqual(feats[-1]["usd_brl"], 5.10)
        # diesel forward-filled from 2026-02-25
        self.assertAlmostEqual(feats[0]["diesel_s10"], 6.30)
        self.assertAlmostEqual(feats[-1]["diesel_s10"], 6.30)

        active = active_macro_regressors(feats)
        self.assertIn("usd_brl", active)
        self.assertIn("diesel_s10", active)
        # selic/ipca not seeded → must not be active
        self.assertNotIn("selic", active)
        self.assertNotIn("ipca_yoy", active)

    def test_future_regressors_carry_macro(self):
        from flv import db as db_mod
        with mock.patch.object(db_mod, "get_conn", lambda: self.conn):
            from flv.model.feature_builder import build_features, build_future_regressors
            feats = build_features("tomate", terminal="CEAGESP")
            fut = build_future_regressors(feats, horizon=5)

        self.assertEqual(len(fut), 5)
        for row in fut:
            self.assertIn("usd_brl", row)
            self.assertAlmostEqual(row["usd_brl"], 5.10)  # persisted last value


if __name__ == "__main__":
    unittest.main()
