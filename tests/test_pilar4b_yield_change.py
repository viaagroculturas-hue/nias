"""Offline tests for Pilar 4.B — Yield model + change-detection + new API routes.

All tests run against an ephemeral SQLite database; no network access is
required. The Yield model tests exercise both the trained-model branch
(when scikit-learn fits successfully) and the climatology-prior fallback
(when the model hasn't been trained).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest import mock

THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _fresh_db():
    """Self-contained SQLite with only the tables Pilar 4.B needs."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE flv_municipalities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ibge_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            state_uf TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        );
        CREATE TABLE flv_cultures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name_pt TEXT,
            main_producers TEXT
        );
        CREATE TABLE flv_production (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER NOT NULL,
            culture_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            production_tons REAL,
            area_harvested_ha REAL,
            source TEXT,
            UNIQUE(mun_id, culture_id, year)
        );
        CREATE TABLE flv_ndvi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER NOT NULL,
            obs_date TEXT NOT NULL,
            ndvi_value REAL NOT NULL,
            source TEXT
        );
        CREATE TABLE flv_climate (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER NOT NULL,
            obs_date TEXT NOT NULL,
            temp_max_c REAL,
            temp_min_c REAL,
            precip_mm REAL
        );
        CREATE TABLE flv_macro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            series TEXT NOT NULL,
            obs_date TEXT NOT NULL,
            value REAL NOT NULL,
            source TEXT,
            UNIQUE(series, obs_date)
        );
        CREATE TABLE flv_sat_scenes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            scene_id TEXT NOT NULL,
            obs_date TEXT NOT NULL,
            cloud_pct REAL,
            asset_url TEXT,
            bbox_json TEXT,
            source TEXT DEFAULT 'planetary-computer',
            UNIQUE(mun_id, platform, scene_id)
        );
        CREATE TABLE flv_lulc_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            crop_class TEXT NOT NULL,
            area_pct REAL NOT NULL,
            area_ha REAL,
            source TEXT DEFAULT 'mapbiomas',
            UNIQUE(mun_id, year, crop_class, source)
        );
        CREATE TABLE flv_crop_classification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            predicted_crop TEXT NOT NULL,
            confidence REAL NOT NULL,
            top_k_json TEXT,
            model_version TEXT DEFAULT 'rf-cv-v1',
            features_json TEXT,
            predicted_at TEXT DEFAULT (datetime('now')),
            UNIQUE(mun_id, year, model_version)
        );
        CREATE TABLE flv_yield_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER NOT NULL,
            culture_slug TEXT NOT NULL,
            year INTEGER NOT NULL,
            yield_ton_ha REAL NOT NULL,
            yield_lower REAL,
            yield_upper REAL,
            ndvi_peak REAL,
            gdd_total REAL,
            features_json TEXT,
            model_version TEXT DEFAULT 'gbr-yield-v1',
            predicted_at TEXT DEFAULT (datetime('now')),
            UNIQUE(mun_id, culture_slug, year, model_version)
        );
        CREATE TABLE flv_cv_anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mun_id INTEGER NOT NULL,
            detected_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            severity TEXT NOT NULL CHECK(severity IN ('info','warn','alert')),
            delta REAL,
            baseline_value REAL,
            current_value REAL,
            details_json TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(mun_id, detected_at, kind)
        );
    """)
    conn.executemany(
        "INSERT INTO flv_municipalities(ibge_code,name,state_uf,lat,lon) VALUES (?,?,?,?,?)",
        [
            ("2910800", "Juazeiro", "BA", -9.42, -40.50),
            ("3520509", "Ibiuna", "SP", -23.65, -47.22),
            ("5107925", "Sorriso", "MT", -12.55, -55.72),
        ],
    )
    conn.executemany(
        "INSERT INTO flv_cultures(slug,name_pt,main_producers) VALUES (?,?,?)",
        [
            ("soja", "Soja", "MT,GO,PR,BA"),
            ("milho", "Milho", "MT,PR,GO,MG"),
            ("tomate", "Tomate", "GO,SP,MG,BA"),
            ("pastagem", "Pastagem", "MT,GO,MG,BA"),
        ],
    )
    conn.commit()
    return path, conn


def _seed_climate(conn, mun_id, year, days=60, tmax=30.0, tmin=18.0, precip=3.0):
    """Insert `days` sequential climate rows for a given municipality/year."""
    start = date(year, 1, 1)
    for i in range(days):
        d = start + timedelta(days=i)
        conn.execute(
            "INSERT INTO flv_climate(mun_id, obs_date, temp_max_c, temp_min_c, precip_mm) "
            "VALUES (?,?,?,?,?)",
            (mun_id, d.isoformat(), tmax, tmin, precip),
        )


def _seed_ndvi(conn, mun_id, year, values, start_month=1):
    start = date(year, start_month, 1)
    for i, v in enumerate(values):
        d = start + timedelta(days=i * 7)
        conn.execute(
            "INSERT INTO flv_ndvi(mun_id, obs_date, ndvi_value, source) VALUES (?,?,?,?)",
            (mun_id, d.isoformat(), v, "test"),
        )


def _seed_production(conn, mun_id, culture_slug, year, tons, area):
    cul = conn.execute("SELECT id FROM flv_cultures WHERE slug = ?", (culture_slug,)).fetchone()
    conn.execute(
        "INSERT INTO flv_production(mun_id, culture_id, year, production_tons, area_harvested_ha, source) "
        "VALUES (?,?,?,?,?,?)",
        (mun_id, cul["id"], year, tons, area, "test"),
    )


# ---------------------------------------------------------------------------
# Yield model
# ---------------------------------------------------------------------------
class TestYieldFeatures(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def test_feature_vector_matches_feature_names_order(self):
        from flv.cv.yield_model import FEATURE_NAMES, extract, extract_vector
        _seed_ndvi(self.conn, 1, 2024, [0.4, 0.6, 0.8, 0.75, 0.55])
        _seed_climate(self.conn, 1, 2024, days=90, tmax=32.0, tmin=20.0, precip=5.0)
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct, area_ha) "
            "VALUES (?,?,?,?,?)",
            (1, 2024, "soja", 0.45, 10000.0),
        )
        self.conn.commit()
        d = extract(self.conn, 1, "soja", 2024)
        self.assertEqual(list(d.keys()), FEATURE_NAMES)
        vec = extract_vector(self.conn, 1, "soja", 2024)
        self.assertEqual(len(vec), len(FEATURE_NAMES))

    def test_ndvi_peak_is_max(self):
        from flv.cv.yield_model import extract
        _seed_ndvi(self.conn, 1, 2024, [0.2, 0.9, 0.4])
        self.conn.commit()
        d = extract(self.conn, 1, "soja", 2024)
        self.assertAlmostEqual(d["ndvi_peak"], 0.9, places=5)

    def test_gdd_accumulates_above_base10(self):
        from flv.cv.yield_model import extract
        _seed_climate(self.conn, 1, 2024, days=10, tmax=30.0, tmin=20.0)  # Tmean=25, GDD=15/day
        self.conn.commit()
        d = extract(self.conn, 1, "soja", 2024)
        self.assertAlmostEqual(d["gdd_total"], 15.0 * 10, places=1)

    def test_heat_stress_days_counted(self):
        from flv.cv.yield_model import extract
        _seed_climate(self.conn, 1, 2024, days=5, tmax=36.0, tmin=24.0)  # 5 heat days
        _seed_climate(self.conn, 1, 2024, days=5, tmax=30.0, tmin=18.0)  # 0 heat days (same year)
        self.conn.commit()
        d = extract(self.conn, 1, "soja", 2024)
        self.assertGreaterEqual(d["heat_stress_days"], 5.0)

    def test_lulc_prior_falls_back_to_previous_year(self):
        from flv.cv.yield_model import extract
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2023, "soja", 0.30),
        )
        self.conn.commit()
        d = extract(self.conn, 1, "soja", 2024)
        self.assertAlmostEqual(d["lulc_crop_pct"], 0.30, places=4)


class TestYieldModel(unittest.TestCase):
    def setUp(self):
        from flv.cv import yield_model as ym
        ym._MODEL_CACHE["gbr"] = None
        ym._MODEL_CACHE["per_crop_bias"] = {}
        if os.path.exists(ym.MODEL_PATH):
            os.unlink(ym.MODEL_PATH)
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        # Reset cache so trained models don't leak between tests.
        from flv.cv import yield_model as ym
        ym._MODEL_CACHE["gbr"] = None
        ym._MODEL_CACHE["per_crop_bias"] = {}
        self.conn.close()
        os.unlink(self.db_path)

    def test_predict_one_uses_prior_when_model_missing(self):
        from flv.cv.yield_model import predict_one
        _seed_ndvi(self.conn, 1, 2024, [0.3, 0.5, 0.7])
        self.conn.commit()
        p = predict_one(self.conn, 1, "soja", 2024)
        self.assertEqual(p["culture_slug"], "soja")
        self.assertEqual(p["source"], "prior")
        self.assertGreater(p["yield_ton_ha"], 0.0)
        self.assertLessEqual(p["yield_lower"], p["yield_ton_ha"])
        self.assertLessEqual(p["yield_ton_ha"], p["yield_upper"])

    def test_train_insufficient_data_returns_status(self):
        from flv.cv.yield_model import train_and_persist
        res = train_and_persist(self.conn, min_samples=12)
        self.assertEqual(res["status"], "insufficient_data")

    def test_train_succeeds_with_enough_rows(self):
        from flv.cv.yield_model import train_and_persist
        # Seed 15 mun-culture-year points with varying yields
        for mid in (1, 2, 3):
            for yr in range(2019, 2024):
                _seed_ndvi(self.conn, mid, yr, [0.3 + 0.05 * yr % 1, 0.6, 0.45])
                _seed_climate(self.conn, mid, yr, days=30, tmax=31.0, tmin=19.0, precip=4.0)
                tons = 3000.0 + (mid * 100) + (yr - 2019) * 50
                area = 1000.0
                _seed_production(self.conn, mid, "soja", yr, tons, area)
        self.conn.commit()
        res = train_and_persist(self.conn, min_samples=6)
        self.assertEqual(res["status"], "trained")
        self.assertGreaterEqual(res["samples"], 6)
        self.assertIn("mape_in_sample_pct", res)

    def test_predict_all_persists_rows(self):
        from flv.cv import yield_model as ym
        _seed_ndvi(self.conn, 1, 2024, [0.5, 0.7])
        _seed_ndvi(self.conn, 2, 2024, [0.4, 0.6])
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2024, "soja", 0.4),
        )
        self.conn.commit()
        n = ym.predict_all(self.conn, year=2024, cultures=["soja", "milho"])
        # 3 muns * 2 cultures = 6 rows
        self.assertEqual(n, 6)
        row = self.conn.execute(
            "SELECT yield_ton_ha, model_version FROM flv_yield_predictions WHERE culture_slug = 'soja' LIMIT 1"
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["model_version"], ym.MODEL_VERSION)
        self.assertGreater(row["yield_ton_ha"], 0.0)


# ---------------------------------------------------------------------------
# Change-detection
# ---------------------------------------------------------------------------
class TestChangeDetection(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _mun_row(self, mid=1):
        return self.conn.execute(
            "SELECT id, lat, state_uf FROM flv_municipalities WHERE id = ?", (mid,)
        ).fetchone()

    def test_ndvi_drop_alert(self):
        from flv.cv.change_detection import detect_ndvi_anomalies
        today = datetime.now(timezone.utc).date()
        # Baseline: 10 months of high NDVI ~0.75
        for i in range(300, 40, -10):
            d = today - timedelta(days=i)
            self.conn.execute(
                "INSERT INTO flv_ndvi(mun_id, obs_date, ndvi_value, source) VALUES (?,?,?,?)",
                (1, d.isoformat(), 0.75, "test"),
            )
        # Recent 30d: NDVI collapsed to 0.35 (delta = -0.40, crosses alert threshold)
        for i in range(25, 0, -5):
            d = today - timedelta(days=i)
            self.conn.execute(
                "INSERT INTO flv_ndvi(mun_id, obs_date, ndvi_value, source) VALUES (?,?,?,?)",
                (1, d.isoformat(), 0.35, "test"),
            )
        self.conn.commit()
        anoms = detect_ndvi_anomalies(self.conn, self._mun_row(1))
        kinds = [a["kind"] for a in anoms]
        self.assertIn("ndvi_drop", kinds)
        drop = next(a for a in anoms if a["kind"] == "ndvi_drop")
        self.assertEqual(drop["severity"], "alert")
        self.assertLess(drop["delta"], -0.18)

    def test_ndvi_drop_no_anomaly_when_stable(self):
        from flv.cv.change_detection import detect_ndvi_anomalies
        today = datetime.now(timezone.utc).date()
        for i in range(300, 0, -10):
            d = today - timedelta(days=i)
            self.conn.execute(
                "INSERT INTO flv_ndvi(mun_id, obs_date, ndvi_value, source) VALUES (?,?,?,?)",
                (1, d.isoformat(), 0.70, "test"),
            )
        self.conn.commit()
        anoms = detect_ndvi_anomalies(self.conn, self._mun_row(1))
        self.assertEqual([a for a in anoms if a["kind"] == "ndvi_drop"], [])

    def test_lulc_shift_detected(self):
        from flv.cv.change_detection import detect_lulc_shift
        # Previous year dominant: pastagem 0.55
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2023, "pastagem", 0.55),
        )
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2023, "soja", 0.20),
        )
        # Current year: soja overtakes pastagem (shift > 15pp)
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2024, "soja", 0.50),
        )
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2024, "pastagem", 0.30),
        )
        self.conn.commit()
        anoms = detect_lulc_shift(self.conn, self._mun_row(1))
        self.assertEqual(len(anoms), 1)
        self.assertEqual(anoms[0]["kind"], "lulc_shift")
        details = json.loads(anoms[0]["details_json"])
        self.assertEqual(details["prior_dominant"], "pastagem")
        self.assertEqual(details["current_dominant"], "soja")

    def test_lulc_shift_skipped_when_same_dominant(self):
        from flv.cv.change_detection import detect_lulc_shift
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2023, "soja", 0.40),
        )
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2024, "soja", 0.45),
        )
        self.conn.commit()
        self.assertEqual(detect_lulc_shift(self.conn, self._mun_row(1)), [])

    def test_run_all_persists(self):
        from flv.cv.change_detection import run_all
        # Seed an LULC shift for mun 1
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2023, "pastagem", 0.60),
        )
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2024, "soja", 0.45),
        )
        self.conn.commit()
        n = run_all(self.conn)
        self.assertGreaterEqual(n, 1)
        rows = self.conn.execute("SELECT kind FROM flv_cv_anomalies").fetchall()
        self.assertIn("lulc_shift", [r["kind"] for r in rows])

    def test_pivot_new_detects_jump(self):
        from flv.cv.change_detection import detect_pivot_new
        now_year = datetime.now(timezone.utc).year
        prior_year = now_year - 1
        # Prior year: 3 S2 scenes + low NDVI
        for i in range(3):
            self.conn.execute(
                "INSERT INTO flv_sat_scenes(mun_id,platform,scene_id,obs_date) VALUES (?,?,?,?)",
                (1, "sentinel-2-l2a", f"p-{i}", f"{prior_year}-06-0{i+1}"),
            )
        _seed_ndvi(self.conn, 1, prior_year, [0.35, 0.38, 0.40])
        # Current year: 15 S2 scenes + high NDVI
        for i in range(15):
            self.conn.execute(
                "INSERT INTO flv_sat_scenes(mun_id,platform,scene_id,obs_date) VALUES (?,?,?,?)",
                (1, "sentinel-2-l2a", f"n-{i:02d}", f"{now_year}-0{(i%9)+1}-01"),
            )
        _seed_ndvi(self.conn, 1, now_year, [0.58, 0.65, 0.70])
        self.conn.commit()
        anoms = detect_pivot_new(self.conn, self._mun_row(1))
        self.assertEqual(len(anoms), 1)
        self.assertEqual(anoms[0]["kind"], "pivot_new")
        self.assertEqual(anoms[0]["severity"], "info")

    def test_is_growing_season_hemispheres(self):
        from flv.cv.change_detection import _is_growing_season
        jan = date(2025, 1, 15)
        jul = date(2025, 7, 15)
        # Southern: Jan is growing, Jul is not
        self.assertTrue(_is_growing_season(-15.0, jan))
        self.assertFalse(_is_growing_season(-15.0, jul))
        # Northern: Jul is growing, Jan is not
        self.assertTrue(_is_growing_season(15.0, jul))
        self.assertFalse(_is_growing_season(15.0, jan))
        # Equatorial: always growing
        self.assertTrue(_is_growing_season(0.0, jan))
        self.assertTrue(_is_growing_season(0.0, jul))


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
class _FakeHandler:
    def __init__(self):
        self.status = None
        self.headers = {}
        self._buf = bytearray()

    def send_response(self, code):
        self.status = code

    def send_header(self, k, v):
        self.headers[k] = v

    def end_headers(self):
        pass

    class _WFile:
        def __init__(self, outer):
            self.outer = outer

        def write(self, b):
            self.outer._buf.extend(b)

    @property
    def wfile(self):
        return self._WFile(self)

    def json(self):
        return json.loads(self._buf.decode())


class TestRoutesYieldAndAnomalies(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _dispatch(self, path):
        from flv import db as db_mod
        from flv.api import routes
        h = _FakeHandler()
        with mock.patch.object(db_mod, "get_conn", lambda: self.conn):
            routes.handle_flv(h, path)
        return h

    def test_yield_endpoint_returns_empty_when_no_rows(self):
        h = self._dispatch("/api/flv/cv/yield/2910800")
        self.assertEqual(h.status, 200)
        body = h.json()
        self.assertEqual(body["count"], 0)
        self.assertEqual(body["municipality"]["ibge_code"], "2910800")

    def test_yield_endpoint_live_predict(self):
        _seed_ndvi(self.conn, 1, 2024, [0.4, 0.6, 0.7])
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id, year, crop_class, area_pct) VALUES (?,?,?,?)",
            (1, 2024, "soja", 0.40),
        )
        self.conn.commit()
        h = self._dispatch("/api/flv/cv/yield/2910800?culture=soja&year=2024&predict=1")
        self.assertEqual(h.status, 200)
        body = h.json()
        self.assertEqual(body["count"], 1)
        item = body["yield_predictions"][0]
        self.assertEqual(item["culture_slug"], "soja")
        self.assertGreater(item["yield_ton_ha"], 0.0)
        self.assertIn("gbr-yield-v1", item["model_version"])

    def test_yield_endpoint_returns_404_for_unknown_mun(self):
        h = self._dispatch("/api/flv/cv/yield/9999999")
        body = h.json()
        self.assertEqual(body.get("error"), "municipality_not_found")

    def test_anomalies_endpoint_default_since(self):
        today = date.today().isoformat()
        self.conn.execute(
            "INSERT INTO flv_cv_anomalies(mun_id, detected_at, kind, severity, delta) "
            "VALUES (?,?,?,?,?)",
            (1, today, "ndvi_drop", "alert", -0.25),
        )
        self.conn.commit()
        h = self._dispatch("/api/flv/cv/anomalies")
        self.assertEqual(h.status, 200)
        body = h.json()
        self.assertEqual(body["count"], 1)
        self.assertEqual(body["by_severity"]["alert"], 1)
        self.assertEqual(body["anomalies"][0]["kind"], "ndvi_drop")
        self.assertEqual(body["anomalies"][0]["ibge_code"], "2910800")

    def test_anomalies_endpoint_filters_by_kind_and_severity(self):
        today = date.today().isoformat()
        for mid, kind, sev in [(1, "ndvi_drop", "alert"), (2, "lulc_shift", "warn"), (3, "pivot_new", "info")]:
            self.conn.execute(
                "INSERT INTO flv_cv_anomalies(mun_id, detected_at, kind, severity) VALUES (?,?,?,?)",
                (mid, today, kind, sev),
            )
        self.conn.commit()
        h = self._dispatch("/api/flv/cv/anomalies?kind=lulc_shift")
        self.assertEqual(h.json()["count"], 1)
        h = self._dispatch("/api/flv/cv/anomalies?severity=alert")
        self.assertEqual(h.json()["count"], 1)

    def test_badge_status_active(self):
        # Seed recent classification without alerts → 'active'
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.conn.execute(
            "INSERT INTO flv_crop_classification(mun_id, year, predicted_crop, confidence, predicted_at) "
            "VALUES (?,?,?,?,?)",
            (1, 2024, "soja", 0.8, now_iso),
        )
        self.conn.commit()
        h = self._dispatch("/api/flv/cv/badge")
        b = h.json()
        self.assertEqual(b["status"], "active")
        self.assertEqual(b["label"], "CV ATIVO")
        self.assertEqual(b["classified_municipalities"], 1)

    def test_badge_status_alerting(self):
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        today = date.today().isoformat()
        self.conn.execute(
            "INSERT INTO flv_crop_classification(mun_id, year, predicted_crop, confidence, predicted_at) "
            "VALUES (?,?,?,?,?)",
            (1, 2024, "soja", 0.8, now_iso),
        )
        self.conn.execute(
            "INSERT INTO flv_cv_anomalies(mun_id, detected_at, kind, severity) VALUES (?,?,?,?)",
            (1, today, "ndvi_drop", "alert"),
        )
        self.conn.commit()
        h = self._dispatch("/api/flv/cv/badge")
        b = h.json()
        self.assertEqual(b["status"], "alerting")
        self.assertIn("CV ATIVO", b["label"])
        self.assertEqual(b["alerts_72h"], 1)

    def test_badge_status_degraded_without_classifications(self):
        h = self._dispatch("/api/flv/cv/badge")
        b = h.json()
        self.assertEqual(b["status"], "degraded")
        self.assertEqual(b["label"], "CV INATIVO")


if __name__ == "__main__":
    unittest.main()
