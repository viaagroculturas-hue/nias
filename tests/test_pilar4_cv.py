"""Offline tests for Pilar 4.A — Sentinel STAC collector, LULC collector,
CV feature extractor, crop classifier, and API routes. All network calls are
mocked so these run without BCB/Planetary-Computer/MapBiomas reachability.
"""
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

THIS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(THIS)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _fresh_db():
    """Isolated SQLite with the minimal schema Pilar 4.A touches."""
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
    """)
    # Seed 3 municipalities + 4 cultures
    conn.execute("INSERT INTO flv_municipalities(ibge_code,name,state_uf,lat,lon) VALUES (?,?,?,?,?)",
                 ("1100015", "Alta Floresta DOeste", "RO", -11.93, -61.99))
    conn.execute("INSERT INTO flv_municipalities(ibge_code,name,state_uf,lat,lon) VALUES (?,?,?,?,?)",
                 ("2910800", "Juazeiro", "BA", -9.42, -40.50))
    conn.execute("INSERT INTO flv_municipalities(ibge_code,name,state_uf,lat,lon) VALUES (?,?,?,?,?)",
                 ("3520509", "Ibiuna", "SP", -23.65, -47.22))
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


class TestSentinelStac(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _patch_db(self):
        from flv import db as db_mod
        return mock.patch.object(db_mod, "get_conn", lambda: self.conn)

    def test_bbox_around_buffer(self):
        from flv.collectors.sentinel_stac import _bbox_around
        bb = _bbox_around(-10.0, -50.0, buffer=0.1)
        self.assertEqual(bb, [-50.1, -10.1, -49.9, -9.9])

    def test_parse_feature_rejects_high_cloud(self):
        from flv.collectors.sentinel_stac import _parse_feature, PLATFORMS
        s2 = [p for p in PLATFORMS if p["collection"] == "sentinel-2-l2a"][0]
        feat = {
            "id": "scene-abc",
            "properties": {"datetime": "2025-03-15T13:50:12Z", "eo:cloud_cover": 55.0},
            "assets": {"B08": {"href": "https://example.com/b08.tif"}},
            "bbox": [-50.1, -10.1, -49.9, -9.9],
        }
        # cloud 55 > max_cloud 30 → rejected
        self.assertIsNone(_parse_feature(feat, s2))

    def test_parse_feature_accepts_clear(self):
        from flv.collectors.sentinel_stac import _parse_feature, PLATFORMS
        s2 = [p for p in PLATFORMS if p["collection"] == "sentinel-2-l2a"][0]
        feat = {
            "id": "scene-clear",
            "properties": {"datetime": "2025-03-15T13:50:12Z", "eo:cloud_cover": 5.0},
            "assets": {"B08": {"href": "https://example.com/b08.tif"}},
            "bbox": [-50.1, -10.1, -49.9, -9.9],
        }
        parsed = _parse_feature(feat, s2)
        self.assertIsNotNone(parsed)
        scene_id, obs_date, cloud, url, bbox = parsed
        self.assertEqual(scene_id, "scene-clear")
        self.assertEqual(obs_date, "2025-03-15")
        self.assertAlmostEqual(cloud, 5.0)
        self.assertEqual(url, "https://example.com/b08.tif")

    def test_parse_feature_sar_ignores_cloud(self):
        from flv.collectors.sentinel_stac import _parse_feature, PLATFORMS
        s1 = [p for p in PLATFORMS if p["collection"] == "sentinel-1-grd"][0]
        feat = {
            "id": "sar-1",
            "properties": {"datetime": "2025-04-01T10:00:00Z"},  # no eo:cloud_cover
            "assets": {"vv": {"href": "https://example.com/vv.tif"}},
            "bbox": [-50, -10, -49, -9],
        }
        parsed = _parse_feature(feat, s1)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[0], "sar-1")
        self.assertIsNone(parsed[2])  # cloud_pct None for SAR

    def test_fetch_one_upserts_to_db(self):
        from flv.collectors import sentinel_stac

        platform = sentinel_stac.PLATFORMS[0]  # S2
        mun = self.conn.execute(
            "SELECT id, ibge_code, name, lat, lon FROM flv_municipalities LIMIT 1"
        ).fetchone()
        bbox = sentinel_stac._bbox_around(mun["lat"], mun["lon"])

        fake_payload = {
            "features": [
                {
                    "id": "S2B_MSIL2A_20250315",
                    "properties": {"datetime": "2025-03-15T13:50:00Z", "eo:cloud_cover": 7.2},
                    "assets": {"B08": {"href": "https://example.com/b08-1.tif"}},
                    "bbox": bbox,
                },
                {
                    "id": "S2B_MSIL2A_20250310",
                    "properties": {"datetime": "2025-03-10T13:50:00Z", "eo:cloud_cover": 3.0},
                    "assets": {"B08": {"href": "https://example.com/b08-2.tif"}},
                    "bbox": bbox,
                },
                # Rejected by cloud filter:
                {
                    "id": "S2B_MSIL2A_20250305",
                    "properties": {"datetime": "2025-03-05T13:50:00Z", "eo:cloud_cover": 85.0},
                    "assets": {"B08": {"href": "https://example.com/b08-3.tif"}},
                    "bbox": bbox,
                },
            ]
        }

        class FakeResp:
            def __init__(self, data): self._d = data
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return self._d.encode()

        import json as _json
        with mock.patch.object(sentinel_stac.urllib.request, "urlopen",
                               return_value=FakeResp(_json.dumps(fake_payload))):
            count = sentinel_stac._fetch_one(self.conn, mun, platform, bbox,
                                             "2025-01-01T00:00:00Z/2025-04-01T00:00:00Z")
        self.assertEqual(count, 2)
        rows = self.conn.execute(
            "SELECT scene_id, cloud_pct FROM flv_sat_scenes ORDER BY obs_date DESC"
        ).fetchall()
        self.assertEqual([r["scene_id"] for r in rows],
                         ["S2B_MSIL2A_20250315", "S2B_MSIL2A_20250310"])

    def test_fetch_all_is_resilient_to_network_errors(self):
        from flv.collectors import sentinel_stac

        with self._patch_db(), mock.patch.object(
            sentinel_stac, "_fetch_one",
            side_effect=ConnectionError("boom")
        ):
            # Should NOT raise even though every inner fetch fails.
            result = sentinel_stac.fetch_all(limit_muns=2)
        self.assertEqual(result, 0)


class TestLULC(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _patch_db(self):
        from flv import db as db_mod
        return mock.patch.object(db_mod, "get_conn", lambda: self.conn)

    def test_mapbiomas_parser_maps_known_class_ids(self):
        from flv.collectors.lulc import _parse_mapbiomas, MAPBIOMAS_CLASS_MAP
        payload = {
            "features": [
                {"classId": MAPBIOMAS_CLASS_MAP["soja"], "areaPct": 0.42, "areaHa": 5000},
                {"classId": MAPBIOMAS_CLASS_MAP["pastagem"], "areaPct": 0.30, "areaHa": 3600},
                {"classId": 99999, "areaPct": 0.1, "areaHa": 100},  # unknown → dropped
            ]
        }
        rows = _parse_mapbiomas(payload)
        self.assertEqual(len(rows), 2)
        slugs = {r[0] for r in rows}
        self.assertEqual(slugs, {"soja", "pastagem"})

    def test_mapbiomas_parser_normalizes_percent_0_100(self):
        from flv.collectors.lulc import _parse_mapbiomas, MAPBIOMAS_CLASS_MAP
        payload = {
            "features": [
                {"classId": MAPBIOMAS_CLASS_MAP["soja"], "areaPct": 42.0, "areaHa": None},
            ]
        }
        rows = _parse_mapbiomas(payload)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][1], 0.42, places=4)

    def test_sidra_fallback_normalizes_tons(self):
        from flv.collectors.lulc import _from_sidra_fallback
        mun = self.conn.execute("SELECT id, ibge_code, state_uf FROM flv_municipalities LIMIT 1").fetchone()
        # 2 cultures with different tons → normalized to 0..1 fractions
        self.conn.execute(
            "INSERT INTO flv_production(mun_id,culture_id,year,production_tons,area_harvested_ha,source) "
            "VALUES (?,?,?,?,?,?)",
            (mun["id"], 1, 2024, 7500.0, 2500.0, "SIDRA-PAM"),  # soja
        )
        self.conn.execute(
            "INSERT INTO flv_production(mun_id,culture_id,year,production_tons,area_harvested_ha,source) "
            "VALUES (?,?,?,?,?,?)",
            (mun["id"], 2, 2024, 2500.0, 800.0, "SIDRA-PAM"),  # milho
        )
        rows = _from_sidra_fallback(self.conn, mun, 2024)
        slugs = {r[0]: r[1] for r in rows}
        self.assertIn("soja", slugs)
        self.assertIn("milho", slugs)
        self.assertAlmostEqual(slugs["soja"], 0.75, places=2)
        self.assertAlmostEqual(slugs["milho"], 0.25, places=2)

    def test_synthetic_fallback_uses_state_uf_hints(self):
        from flv.collectors.lulc import _synthetic_fallback
        # Ibiuna/SP — tomate lists SP first in main_producers, so should get a share.
        mun = self.conn.execute(
            "SELECT id, ibge_code, state_uf FROM flv_municipalities WHERE state_uf='SP'"
        ).fetchone()
        rows = _synthetic_fallback(self.conn, mun, 2024)
        slugs = {r[0] for r in rows}
        # Tomate has 'GO,SP,MG,BA' — SP is second, so tomate should be in results.
        self.assertIn("tomate", slugs)

    def test_fetch_for_mun_escalates_through_fallbacks(self):
        from flv.collectors import lulc

        mun = self.conn.execute(
            "SELECT id, ibge_code, name, state_uf FROM flv_municipalities LIMIT 1"
        ).fetchone()

        # 1) MapBiomas reachable → used
        with mock.patch.object(lulc, "_try_mapbiomas", return_value=[("soja", 0.5, 1000.0)]):
            n = lulc._fetch_for_mun(self.conn, mun, 2024)
        self.assertEqual(n, 1)
        src = self.conn.execute(
            "SELECT source FROM flv_lulc_stats WHERE mun_id = ? AND year = 2024",
            (mun["id"],),
        ).fetchone()["source"]
        self.assertEqual(src, "mapbiomas")

        # 2) MapBiomas empty, SIDRA has data → sidra-pam-derived
        self.conn.execute("DELETE FROM flv_lulc_stats")
        self.conn.execute(
            "INSERT INTO flv_production(mun_id,culture_id,year,production_tons) "
            "VALUES (?,?,?,?)",
            (mun["id"], 1, 2024, 1000.0),
        )
        with mock.patch.object(lulc, "_try_mapbiomas", return_value=[]):
            n = lulc._fetch_for_mun(self.conn, mun, 2024)
        self.assertGreaterEqual(n, 1)
        src = self.conn.execute(
            "SELECT source FROM flv_lulc_stats WHERE mun_id = ? AND year = 2024",
            (mun["id"],),
        ).fetchone()["source"]
        self.assertEqual(src, "sidra-pam-derived")


class TestFeatureExtractor(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def test_extract_vector_length_matches_feature_names(self):
        from flv.cv.feature_extractor import extract_vector, FEATURE_NAMES
        mun = self.conn.execute("SELECT id FROM flv_municipalities LIMIT 1").fetchone()
        vec = extract_vector(self.conn, mun["id"], 2024)
        self.assertEqual(len(vec), len(FEATURE_NAMES))

    def test_extract_aggregates_ndvi_and_climate(self):
        from flv.cv.feature_extractor import extract
        mun = self.conn.execute("SELECT id FROM flv_municipalities LIMIT 1").fetchone()
        # NDVI — 4 points in 2024 with rising trend
        for i, v in enumerate([0.40, 0.50, 0.60, 0.70]):
            self.conn.execute(
                "INSERT INTO flv_ndvi(mun_id,obs_date,ndvi_value) VALUES (?,?,?)",
                (mun["id"], f"2024-0{i+3}-15", v),
            )
        # Climate — 3 days with one heat-stress event
        self.conn.executemany(
            "INSERT INTO flv_climate(mun_id,obs_date,temp_max_c,temp_min_c,precip_mm) VALUES (?,?,?,?,?)",
            [
                (mun["id"], "2024-03-01", 30.0, 18.0, 5.0),
                (mun["id"], "2024-03-02", 36.0, 20.0, 0.0),
                (mun["id"], "2024-03-03", 32.0, 19.0, 2.0),
            ],
        )
        self.conn.commit()
        feats = extract(self.conn, mun["id"], 2024)
        self.assertAlmostEqual(feats["ndvi_mean"], 0.55, places=2)
        self.assertAlmostEqual(feats["ndvi_max"], 0.70, places=2)
        self.assertGreater(feats["ndvi_slope"], 0.0)
        self.assertAlmostEqual(feats["precip_total"], 7.0, places=2)
        self.assertEqual(feats["heat_stress_days"], 1.0)

    def test_label_for_picks_dominant_class(self):
        from flv.cv.feature_extractor import label_for
        mun = self.conn.execute("SELECT id FROM flv_municipalities LIMIT 1").fetchone()
        self.conn.executemany(
            "INSERT INTO flv_lulc_stats(mun_id,year,crop_class,area_pct,source) VALUES (?,?,?,?,?)",
            [
                (mun["id"], 2024, "soja", 0.50, "mapbiomas"),
                (mun["id"], 2024, "milho", 0.30, "mapbiomas"),
                (mun["id"], 2024, "pastagem", 0.20, "mapbiomas"),
            ],
        )
        self.conn.commit()
        self.assertEqual(label_for(self.conn, mun["id"], 2024), "soja")

    def test_label_for_falls_back_to_prior_year(self):
        from flv.cv.feature_extractor import label_for
        mun = self.conn.execute("SELECT id FROM flv_municipalities LIMIT 1").fetchone()
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id,year,crop_class,area_pct) VALUES (?,?,?,?)",
            (mun["id"], 2022, "milho", 0.9),
        )
        self.conn.commit()
        self.assertEqual(label_for(self.conn, mun["id"], 2024), "milho")


class TestCropClassifier(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()
        self._seed_training_rows()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _seed_training_rows(self):
        """Build enough (mun, year) rows across classes for a non-trivial fit."""
        muns = self.conn.execute("SELECT id FROM flv_municipalities").fetchall()
        # Two cycles per muni × 2 years × 3 muns = 6 samples; assign alternating
        # labels so we have ≥2 classes with ≥2 samples each.
        data = [
            (muns[0]["id"], 2022, "soja",     0.7, 0.6, 0.8),
            (muns[0]["id"], 2023, "soja",     0.72, 0.58, 0.82),
            (muns[1]["id"], 2022, "pastagem", 0.5, 0.45, 0.55),
            (muns[1]["id"], 2023, "pastagem", 0.48, 0.44, 0.53),
            (muns[2]["id"], 2022, "tomate",   0.6, 0.55, 0.70),
            (muns[2]["id"], 2023, "tomate",   0.63, 0.57, 0.72),
        ]
        for mun_id, year, crop, ndvi_a, ndvi_b, ndvi_c in data:
            self.conn.execute(
                "INSERT INTO flv_lulc_stats(mun_id,year,crop_class,area_pct,source) VALUES (?,?,?,?,?)",
                (mun_id, year, crop, 0.6, "mapbiomas"),
            )
            # A second minority class so the dominant label is unambiguous.
            self.conn.execute(
                "INSERT INTO flv_lulc_stats(mun_id,year,crop_class,area_pct,source) VALUES (?,?,?,?,?)",
                (mun_id, year, "floresta", 0.2, "mapbiomas"),
            )
            for i, v in enumerate([ndvi_a, ndvi_b, ndvi_c]):
                self.conn.execute(
                    "INSERT INTO flv_ndvi(mun_id,obs_date,ndvi_value) VALUES (?,?,?)",
                    (mun_id, f"{year}-0{i+3}-10", v),
                )
            self.conn.execute(
                "INSERT INTO flv_climate(mun_id,obs_date,temp_max_c,temp_min_c,precip_mm) VALUES (?,?,?,?,?)",
                (mun_id, f"{year}-03-15", 30.0, 18.0, 3.5),
            )
        self.conn.commit()

    def _patch_db(self):
        from flv import db as db_mod
        return mock.patch.object(db_mod, "get_conn", lambda: self.conn)

    def test_train_fits_and_reports_metrics(self):
        from flv.cv import crop_classifier
        # Point persistence path somewhere ephemeral
        with mock.patch.object(crop_classifier, "MODEL_PATH", self.db_path + ".pkl"):
            with self._patch_db():
                res = crop_classifier.train_and_persist(self.conn, min_samples=4)
        self.assertEqual(res["status"], "trained")
        self.assertGreaterEqual(res["samples"], 4)
        self.assertIn("soja", res["classes"])
        self.assertIn("pastagem", res["classes"])
        # Fully-separable toy dataset → in-sample accuracy must be perfect.
        self.assertAlmostEqual(res["accuracy_in_sample"], 1.0, places=3)

    def test_predict_all_persists_rows(self):
        from flv.cv import crop_classifier
        with mock.patch.object(crop_classifier, "MODEL_PATH", self.db_path + ".pkl"):
            with self._patch_db():
                crop_classifier.train_and_persist(self.conn, min_samples=4)
                n = crop_classifier.predict_all(self.conn, year=2023)
        self.assertEqual(n, 3)  # 3 muns
        rows = self.conn.execute(
            "SELECT predicted_crop, confidence, model_version FROM flv_crop_classification"
        ).fetchall()
        self.assertEqual(len(rows), 3)
        for r in rows:
            self.assertIn(r["predicted_crop"], {"soja", "pastagem", "tomate", "floresta"})
            self.assertGreaterEqual(r["confidence"], 0.0)
            self.assertLessEqual(r["confidence"], 1.0)
            self.assertEqual(r["model_version"], "rf-cv-v1")

    def test_insufficient_data_returns_status(self):
        from flv.cv import crop_classifier
        # Wipe labels → not enough samples
        self.conn.execute("DELETE FROM flv_lulc_stats")
        self.conn.commit()
        with self._patch_db():
            res = crop_classifier.train_and_persist(self.conn, min_samples=4)
        self.assertEqual(res["status"], "insufficient_data")

    def test_register_is_noop_in_pr4(self):
        """PR#4 intentionally does NOT wire CV into the retrain controller —
        that's PR#6 (Pilar 4.C). Ensure register() returns False so the
        ensemble's callback isn't clobbered."""
        from flv.cv import crop_classifier
        from flv.model import retrain_controller as rc

        # Install a sentinel callback we can detect later.
        sentinel = lambda *a, **kw: "ensemble-was-here"
        rc.register_trainer(sentinel)
        self.assertFalse(crop_classifier.register())
        # Ensemble's callback must survive the CV register() call.
        self.assertIs(rc._trainer_cb, sentinel)


class TestCVRoutes(unittest.TestCase):
    def setUp(self):
        self.db_path, self.conn = _fresh_db()
        self.conn.execute(
            "INSERT INTO flv_crop_classification(mun_id,year,predicted_crop,confidence,top_k_json,model_version) "
            "VALUES (?,?,?,?,?,?)",
            (1, 2024, "soja", 0.87, '{"soja":0.87,"milho":0.09}', "rf-cv-v1"),
        )
        self.conn.execute(
            "INSERT INTO flv_sat_scenes(mun_id,platform,scene_id,obs_date,cloud_pct,asset_url) "
            "VALUES (?,?,?,?,?,?)",
            (1, "sentinel-2-l2a", "S2-test-1", "2025-03-15", 5.0, "https://x/b08.tif"),
        )
        self.conn.execute(
            "INSERT INTO flv_lulc_stats(mun_id,year,crop_class,area_pct) VALUES (?,?,?,?)",
            (1, 2024, "soja", 0.6),
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.unlink(self.db_path)

    def _patch_db(self):
        from flv import db as db_mod
        return [
            mock.patch.object(db_mod, "get_conn", lambda: self.conn),
            mock.patch.object(db_mod, "query", lambda sql, args=(): [dict(r) for r in self.conn.execute(sql, args).fetchall()]),
        ]

    def test_get_cv_classification_by_ibge_code(self):
        from flv.api import routes
        patches = self._patch_db()
        for p in patches: p.start()
        try:
            data = routes._get_cv_classification("1100015", {})
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["classifications"][0]["predicted_crop"], "soja")
            self.assertEqual(data["municipality"]["ibge_code"], "1100015")
        finally:
            for p in patches: p.stop()

    def test_get_cv_scenes_by_platform_filter(self):
        from flv.api import routes
        patches = self._patch_db()
        for p in patches: p.start()
        try:
            data = routes._get_cv_scenes("1100015", {"platform": "sentinel-2-l2a"})
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["scenes"][0]["scene_id"], "S2-test-1")
            # Filter by a platform that has no rows
            data2 = routes._get_cv_scenes("1100015", {"platform": "sentinel-1-grd"})
            self.assertEqual(data2["count"], 0)
        finally:
            for p in patches: p.stop()

    def test_get_cv_health_reports_coverage(self):
        from flv.api import routes
        patches = self._patch_db()
        for p in patches: p.start()
        try:
            data = routes._get_cv_health({})
            self.assertEqual(data["model_version"], "rf-cv-v1")
            self.assertEqual(data["coverage"]["total_municipalities"], 3)
            self.assertEqual(data["coverage"]["classified_municipalities"], 1)
            self.assertAlmostEqual(data["coverage"]["coverage_pct"], 33.33, places=1)
            self.assertEqual(len(data["class_distribution"]), 1)
            self.assertEqual(data["class_distribution"][0]["crop"], "soja")
        finally:
            for p in patches: p.stop()

    def test_cv_classification_unknown_mun(self):
        from flv.api import routes
        patches = self._patch_db()
        for p in patches: p.start()
        try:
            data = routes._get_cv_classification("9999999", {})
            self.assertEqual(data.get("error"), "municipality_not_found")
        finally:
            for p in patches: p.stop()


if __name__ == "__main__":
    unittest.main()
