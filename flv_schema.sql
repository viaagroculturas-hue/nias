-- FLV Market Anticipation — Schema SQLite
-- NIA$ — Núcleo de Inteligência Agro-Sul

PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS flv_municipalities (
    id          INTEGER PRIMARY KEY,
    ibge_code   TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    state_uf    TEXT NOT NULL,
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    is_producer INTEGER DEFAULT 1,
    ceasa_ref   TEXT,
    inmet_station TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS flv_cultures (
    id          INTEGER PRIMARY KEY,
    slug        TEXT UNIQUE NOT NULL,
    name_pt     TEXT NOT NULL,
    category    TEXT CHECK(category IN ('fruta','legume','verdura')),
    unit        TEXT DEFAULT 'R$/kg',
    sidra_code  TEXT,
    conab_key   TEXT,
    shelf_life_days INTEGER,
    seasonality_json TEXT,
    main_producers TEXT
);

CREATE TABLE IF NOT EXISTS flv_mun_culture (
    mun_id      INTEGER REFERENCES flv_municipalities(id),
    culture_id  INTEGER REFERENCES flv_cultures(id),
    area_mha    REAL,
    yield_t_ha  REAL,
    PRIMARY KEY (mun_id, culture_id)
);

CREATE TABLE IF NOT EXISTS flv_ceasa_prices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    culture_id  INTEGER NOT NULL REFERENCES flv_cultures(id),
    mun_id      INTEGER REFERENCES flv_municipalities(id),
    terminal    TEXT NOT NULL,
    price_date  TEXT NOT NULL,
    price_min   REAL,
    price_avg   REAL NOT NULL,
    price_max   REAL,
    volume_kg   REAL,
    source      TEXT DEFAULT 'CONAB',
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(culture_id, terminal, price_date)
);

CREATE TABLE IF NOT EXISTS flv_climate (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mun_id      INTEGER NOT NULL REFERENCES flv_municipalities(id),
    obs_date    TEXT NOT NULL,
    temp_max_c  REAL,
    temp_min_c  REAL,
    precip_mm   REAL,
    humidity_pct REAL,
    wind_ms     REAL,
    insolation_h REAL,
    source      TEXT DEFAULT 'INMET',
    UNIQUE(mun_id, obs_date, source)
);

CREATE TABLE IF NOT EXISTS flv_ndvi (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mun_id      INTEGER NOT NULL REFERENCES flv_municipalities(id),
    culture_id  INTEGER REFERENCES flv_cultures(id),
    obs_date    TEXT NOT NULL,
    ndvi_value  REAL NOT NULL,
    ndvi_anomaly REAL,
    source      TEXT DEFAULT 'SATVeg',
    UNIQUE(mun_id, obs_date, source)
);

CREATE TABLE IF NOT EXISTS flv_production (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mun_id      INTEGER NOT NULL REFERENCES flv_municipalities(id),
    culture_id  INTEGER NOT NULL REFERENCES flv_cultures(id),
    year        INTEGER NOT NULL,
    area_harvested_ha REAL,
    production_tons   REAL,
    source      TEXT DEFAULT 'SIDRA',
    UNIQUE(mun_id, culture_id, year)
);

CREATE TABLE IF NOT EXISTS flv_predictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    culture_id  INTEGER NOT NULL REFERENCES flv_cultures(id),
    mun_id      INTEGER REFERENCES flv_municipalities(id),
    terminal    TEXT,
    generated_at TEXT DEFAULT (datetime('now')),
    target_date TEXT NOT NULL,
    horizon_days INTEGER,
    predicted_price REAL NOT NULL,
    price_lower_80  REAL,
    price_upper_80  REAL,
    trend_direction TEXT CHECK(trend_direction IN ('alta','baixa','estavel')),
    confidence_pct  REAL,
    model_version   TEXT DEFAULT 'prophet-v1',
    features_json   TEXT
);

CREATE TABLE IF NOT EXISTS flv_alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    culture_id  INTEGER REFERENCES flv_cultures(id),
    mun_id      INTEGER REFERENCES flv_municipalities(id),
    region_key  TEXT NOT NULL,
    alert_type  TEXT NOT NULL,
    severity    TEXT CHECK(severity IN ('amarelo','laranja','vermelho')),
    trigger_value    REAL,
    threshold_value  REAL,
    impact_supply_pct REAL,
    impact_price_pct  REAL,
    message     TEXT,
    valid_until TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS flv_accuracy (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    prediction_id INTEGER REFERENCES flv_predictions(id),
    actual_price REAL NOT NULL,
    actual_date  TEXT NOT NULL,
    mape_pct     REAL,
    evaluated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_prices_cult_date ON flv_ceasa_prices(culture_id, price_date);
CREATE INDEX IF NOT EXISTS idx_climate_mun_date ON flv_climate(mun_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_ndvi_mun_date    ON flv_ndvi(mun_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_pred_cult_target  ON flv_predictions(culture_id, target_date);
CREATE INDEX IF NOT EXISTS idx_alerts_sev_date   ON flv_alerts(severity, created_at);
