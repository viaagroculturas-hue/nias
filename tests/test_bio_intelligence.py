import sqlite3

from core.bio_intelligence import (
    calculate_ndvi,
    compare_ndvi_current_vs_historical,
    evaluate_db_supply_risk,
    generate_supply_risk_alert,
    process_sentinel2_pole,
    recognize_spectral_signature,
)


def test_calculate_ndvi_from_sentinel2_bands():
    ndvi = calculate_ndvi([[0.80, 0.30]], [[0.20, 0.30]])

    assert round(ndvi[0][0], 4) == 0.6
    assert ndvi[0][1] == 0.0


def test_generate_supply_risk_alert_when_drop_reaches_15_percent():
    comparison = compare_ndvi_current_vs_historical(
        "cristalina_go",
        0.51,
        [0.60, 0.61, 0.59],
        obs_date="2026-04-28",
    )

    alert = generate_supply_risk_alert(comparison, culture_slug="tomate", municipality="Cristalina-GO")

    assert comparison.risk_triggered is True
    assert alert is not None
    assert alert["type"] == "Risco de Oferta"
    assert alert["alert_type"] == "risco_oferta"
    assert alert["severity"] == "laranja"
    assert alert["threshold_value"] == 0.51
    assert "15.0% abaixo" in alert["message"]


def test_recognize_spectral_signature_detects_hortifruti_patch():
    red = [[0.18 for _ in range(5)] for _ in range(5)]
    nir = [[0.72 for _ in range(5)] for _ in range(5)]
    green = [[0.20 for _ in range(5)] for _ in range(5)]
    swir = [[0.36 for _ in range(5)] for _ in range(5)]
    red_edge = [[0.26 for _ in range(5)] for _ in range(5)]

    detections = recognize_spectral_signature(
        {"B04": red, "B08": nir, "B03": green, "B11": swir, "B05": red_edge},
        min_pixels=10,
    )

    assert len(detections) == 1
    detection = detections[0]
    assert detection.crop_type == "hortifruti_irrigado"
    assert detection.pixel_count == 25
    assert detection.confidence >= 0.7


def test_process_sentinel2_pole_returns_ndvi_signatures_and_alert():
    bands = {
        "B04": [[0.18 for _ in range(4)] for _ in range(4)],
        "B08": [[0.70 for _ in range(4)] for _ in range(4)],
        "B03": [[0.20 for _ in range(4)] for _ in range(4)],
        "B11": [[0.35 for _ in range(4)] for _ in range(4)],
        "B05": [[0.25 for _ in range(4)] for _ in range(4)],
    }

    result = process_sentinel2_pole(
        "vale_sao_francisco",
        bands,
        historical_ndvi=[0.72, 0.73, 0.71],
        obs_date="2026-04-28",
        culture_slug="uva",
        municipality="Petrolina-PE",
    )

    assert result["ndvi"]["risk_triggered"] is True
    assert result["alert"]["type"] == "Risco de Oferta"
    assert result["new_production_points"]


def test_evaluate_db_supply_risk_persists_alert():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE flv_municipalities (
            id INTEGER PRIMARY KEY,
            ibge_code TEXT,
            name TEXT,
            state_uf TEXT
        );
        CREATE TABLE flv_cultures (
            id INTEGER PRIMARY KEY,
            slug TEXT,
            name_pt TEXT
        );
        CREATE TABLE flv_ndvi (
            mun_id INTEGER,
            culture_id INTEGER,
            obs_date TEXT,
            ndvi_value REAL
        );
        CREATE TABLE flv_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            culture_id INTEGER,
            mun_id INTEGER,
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
        INSERT INTO flv_municipalities VALUES (1, '5206206', 'Cristalina', 'GO');
        INSERT INTO flv_cultures VALUES (1, 'tomate', 'Tomate Mesa');
        INSERT INTO flv_ndvi VALUES (1, 1, '2026-04-01', 0.62);
        INSERT INTO flv_ndvi VALUES (1, 1, '2026-04-08', 0.60);
        INSERT INTO flv_ndvi VALUES (1, 1, '2026-04-15', 0.61);
        INSERT INTO flv_ndvi VALUES (1, 1, '2026-04-28', 0.50);
        """
    )

    alerts = evaluate_db_supply_risk(conn)
    stored = conn.execute("SELECT * FROM flv_alerts").fetchall()

    assert len(alerts) == 1
    assert len(stored) == 1
    assert stored[0]["alert_type"] == "risco_oferta"
    assert stored[0]["region_key"] == "5206206_tomate"
