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

-- Log de retreinos de modelo (MLOps / Pilar 3).
-- Um registro por decisao do retrain_controller: 'completed', 'failed', 'deferred'.
CREATE TABLE IF NOT EXISTS flv_model_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    culture_slug    TEXT NOT NULL,
    terminal        TEXT,
    model_version   TEXT,
    started_at      TEXT DEFAULT (datetime('now')),
    finished_at     TEXT,
    mape_before     REAL,
    mape_after      REAL,
    trigger_reason  TEXT,
    status          TEXT CHECK(status IN ('completed','failed','deferred','pending')) DEFAULT 'pending',
    notes           TEXT
);

-- Indicadores macroeconomicos (USD PTAX, Selic, IPCA, Diesel ANP).
-- Consumidos pelo feature_builder como regressores opcionais.
CREATE TABLE IF NOT EXISTS flv_macro (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    series      TEXT NOT NULL,
    obs_date    TEXT NOT NULL,
    value       REAL NOT NULL,
    source      TEXT NOT NULL DEFAULT 'BCB',
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(series, obs_date)
);

CREATE INDEX IF NOT EXISTS idx_prices_cult_date ON flv_ceasa_prices(culture_id, price_date);
CREATE INDEX IF NOT EXISTS idx_climate_mun_date ON flv_climate(mun_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_ndvi_mun_date    ON flv_ndvi(mun_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_pred_cult_target  ON flv_predictions(culture_id, target_date);
CREATE INDEX IF NOT EXISTS idx_alerts_sev_date   ON flv_alerts(severity, created_at);
CREATE INDEX IF NOT EXISTS idx_macro_series_date ON flv_macro(series, obs_date);
CREATE INDEX IF NOT EXISTS idx_model_runs_cult    ON flv_model_runs(culture_slug, terminal, started_at);
CREATE INDEX IF NOT EXISTS idx_accuracy_pred_id   ON flv_accuracy(prediction_id);
CREATE INDEX IF NOT EXISTS idx_accuracy_date      ON flv_accuracy(actual_date);

-- =========================================================================
-- Pilar 4.A — Visao Computacional / Reconhecimento de safra via satelite.
-- Populated by flv/collectors/sentinel_stac.py + flv/collectors/lulc.py
-- Consumed by flv/cv/crop_classifier.py (RandomForest multi-temporal).
-- =========================================================================

-- Cenas de satelite disponiveis por municipio (metadados STAC, sem raster).
-- Fonte: Microsoft Planetary Computer STAC API (sem auth, publico).
CREATE TABLE IF NOT EXISTS flv_sat_scenes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mun_id      INTEGER NOT NULL REFERENCES flv_municipalities(id),
    platform    TEXT NOT NULL,         -- 'sentinel-2-l2a' | 'sentinel-1-grd' | 'landsat-c2-l2'
    scene_id    TEXT NOT NULL,         -- STAC item id
    obs_date    TEXT NOT NULL,         -- YYYY-MM-DD
    cloud_pct   REAL,                  -- eo:cloud_cover (null para SAR)
    asset_url   TEXT,                  -- URL do COG principal (B04/B08 ou VV)
    bbox_json   TEXT,                  -- [minx,miny,maxx,maxy]
    source      TEXT DEFAULT 'planetary-computer',
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(mun_id, platform, scene_id)
);

-- Estatisticas de uso/cobertura do solo por municipio x ano.
-- Fonte primaria: MapBiomas Colecao (AR/BR/UY/PY/BO). Fallback: SIDRA PAM.
CREATE TABLE IF NOT EXISTS flv_lulc_stats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    mun_id      INTEGER NOT NULL REFERENCES flv_municipalities(id),
    year        INTEGER NOT NULL,
    crop_class  TEXT NOT NULL,         -- 'soja' | 'milho' | 'tomate' | 'pastagem' | 'floresta' | ...
    area_pct    REAL NOT NULL,         -- 0..1 (fracao da area municipal)
    area_ha     REAL,                  -- hectares (quando disponivel)
    source      TEXT DEFAULT 'mapbiomas',
    UNIQUE(mun_id, year, crop_class, source)
);

-- Resultado do classificador de cultura (Pilar 4.A).
-- Populada pelo flv/cv/crop_classifier.predict_all().
CREATE TABLE IF NOT EXISTS flv_crop_classification (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    mun_id          INTEGER NOT NULL REFERENCES flv_municipalities(id),
    year            INTEGER NOT NULL,
    predicted_crop  TEXT NOT NULL,      -- slug em flv_cultures (ou 'outros')
    confidence      REAL NOT NULL,      -- 0..1
    top_k_json      TEXT,               -- JSON: {'soja':0.42,'milho':0.31,...}
    model_version   TEXT DEFAULT 'rf-cv-v1',
    features_json   TEXT,               -- vetor de features usado
    predicted_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(mun_id, year, model_version)
);

CREATE INDEX IF NOT EXISTS idx_sat_scenes_mun_date ON flv_sat_scenes(mun_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_lulc_mun_year       ON flv_lulc_stats(mun_id, year);
CREATE INDEX IF NOT EXISTS idx_cv_class_mun        ON flv_crop_classification(mun_id, year);

-- Tabela de Produtores (RJ e outros estados)
CREATE TABLE IF NOT EXISTS flv_producers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    document    TEXT UNIQUE,
    phone       TEXT,
    email       TEXT,
    address     TEXT,
    city        TEXT NOT NULL,
    state_uf    TEXT NOT NULL DEFAULT 'RJ',
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    products    TEXT NOT NULL, -- JSON array de produtos
    production_volume TEXT, -- JSON com volumes por produto
    certifications TEXT, -- Orgânico, Fair Trade, etc
    market_channel TEXT CHECK(market_channel IN ('CEASA','Mercado Local','Exportação','Direto','Misto')),
    status      TEXT DEFAULT 'ativo' CHECK(status IN ('ativo','inativo','pendente')),
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_producers_state ON flv_producers(state_uf);
CREATE INDEX IF NOT EXISTS idx_producers_city ON flv_producers(city);
CREATE INDEX IF NOT EXISTS idx_producers_status ON flv_producers(status);

-- Tabela de Produtores em Recuperação Judicial
CREATE TABLE IF NOT EXISTS flv_producers_rj (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    cnpj        TEXT UNIQUE,
    process_number TEXT,
    court       TEXT,
    judicial_status TEXT DEFAULT 'em_recuperacao' CHECK(judicial_status IN ('em_recuperacao', 'recuperacao_aprovada', 'falencia', 'reorganizado')),
    phone       TEXT,
    email       TEXT,
    address     TEXT,
    city        TEXT NOT NULL,
    state_uf    TEXT NOT NULL DEFAULT 'RJ',
    lat         REAL NOT NULL,
    lon         REAL NOT NULL,
    products    TEXT NOT NULL,
    production_volume TEXT,
    annual_revenue REAL,
    employees   INTEGER,
    debts_total REAL,
    recovery_plan TEXT,
    entry_date  TEXT,
    status      TEXT DEFAULT 'ativo',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_producers_rj_city ON flv_producers_rj(city);
CREATE INDEX IF NOT EXISTS idx_producers_rj_status ON flv_producers_rj(judicial_status);
