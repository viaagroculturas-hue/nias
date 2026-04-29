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

CREATE VIEW IF NOT EXISTS flv_prices AS
    SELECT * FROM flv_ceasa_prices;

CREATE TABLE IF NOT EXISTS flv_sovereign_entities (
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    name TEXT NOT NULL,
    lat REAL,
    lon REAL,
    country TEXT,
    state_uf TEXT,
    score_soberano REAL NOT NULL,
    components_json TEXT,
    status_color TEXT,
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS flv_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    obs_ts TEXT NOT NULL,
    domain TEXT,
    entity_type TEXT,
    entity_id TEXT,
    change_type TEXT,
    severity TEXT,
    score_before REAL,
    score_after REAL,
    payload_json TEXT
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

-- Indicadores macroeconômicos (economia + energia/logística)
CREATE TABLE IF NOT EXISTS flv_macro_indicators (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    obs_date    TEXT NOT NULL UNIQUE,
    diesel_brl_l REAL,
    diesel_change_pct REAL,
    usd_brl     REAL,
    selic_pct   REAL,
    ipca_yoy_pct REAL,
    source      TEXT DEFAULT 'BCB/ANP',
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Notícias (NLP leve) + índice de risco agregado
CREATE TABLE IF NOT EXISTS flv_news_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    obs_ts      TEXT NOT NULL,
    source      TEXT,
    title       TEXT,
    url         TEXT,
    risk_score  REAL,
    tags_json   TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS flv_news_risk_daily (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    obs_date    TEXT NOT NULL UNIQUE,
    risk_index  REAL NOT NULL,
    top_tags_json TEXT,
    sources_json TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Teleconexões (clima global): ONI (El Niño) + Atlântico Norte (proxy/índice)
CREATE TABLE IF NOT EXISTS flv_global_climate (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    obs_date    TEXT NOT NULL UNIQUE,
    oni         REAL,
    atl_north_warm_idx REAL,
    source      TEXT DEFAULT 'NOAA/ESRL',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_prices_cult_date ON flv_ceasa_prices(culture_id, price_date);
CREATE INDEX IF NOT EXISTS idx_climate_mun_date ON flv_climate(mun_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_ndvi_mun_date    ON flv_ndvi(mun_id, obs_date);
CREATE INDEX IF NOT EXISTS idx_pred_cult_target  ON flv_predictions(culture_id, target_date);
CREATE INDEX IF NOT EXISTS idx_alerts_sev_date   ON flv_alerts(severity, created_at);
CREATE INDEX IF NOT EXISTS idx_macro_date        ON flv_macro_indicators(obs_date);
CREATE INDEX IF NOT EXISTS idx_news_evt_ts       ON flv_news_events(obs_ts);
CREATE INDEX IF NOT EXISTS idx_news_daily_date   ON flv_news_risk_daily(obs_date);
CREATE INDEX IF NOT EXISTS idx_global_clim_date  ON flv_global_climate(obs_date);

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

-- ═══════════════════════════════════════════════════════════════
-- NIA$ SOBERANO DIGITAL v5.0 - EXPANSÕES
-- ═══════════════════════════════════════════════════════════════

-- Expansão da tabela flv_producers_rj com campos de score e histórico
ALTER TABLE flv_producers_rj ADD COLUMN credit_score_2026 REAL;
ALTER TABLE flv_producers_rj ADD COLUMN credit_history_24m TEXT; -- JSON array com histórico mensal
ALTER TABLE flv_producers_rj ADD COLUMN director_changes TEXT; -- JSON array de alterações de diretoria
ALTER TABLE flv_producers_rj ADD COLUMN new_partners TEXT; -- JSON array de novos sócios
ALTER TABLE flv_producers_rj ADD COLUMN administrator_changes TEXT; -- JSON array de mudanças de administradores
ALTER TABLE flv_producers_rj ADD COLUMN last_judicial_update TEXT; -- Última atualização do processo
ALTER TABLE flv_producers_rj ADD COLUMN process_status_detail TEXT; -- Detalhamento do status processual
ALTER TABLE flv_producers_rj ADD COLUMN creditor_list TEXT; -- JSON com principais credores
ALTER TABLE flv_producers_rj ADD COLUMN asset_auctions TEXT; -- JSON com leilões de ativos

-- Tabela de Distribuidores (300 maiores)
CREATE TABLE IF NOT EXISTS flv_distributors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    cnpj        TEXT UNIQUE,
    category    TEXT CHECK(category IN ('varejo', 'atacado', 'distribuidor', 'cooperativa', 'industria')),
    segment     TEXT, -- 'insumos', 'graos', 'hortifruti', 'maquinas', 'logistica'
    market_cap  REAL,
    annual_revenue REAL,
    revenue_growth_pct REAL, -- Crescimento anual
    employees   INTEGER,
    stores_count INTEGER,
    warehouses_count INTEGER,
    states_coverage TEXT, -- JSON array de estados atendidos
    main_products TEXT, -- JSON array de produtos principais
    key_suppliers TEXT, -- JSON array de fornecedores chave
    risk_level  TEXT CHECK(risk_level IN ('baixo', 'medio', 'alto', 'critico')),
    lat         REAL,
    lon         REAL,
    city        TEXT,
    state_uf    TEXT,
    status      TEXT DEFAULT 'ativo',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_distributors_category ON flv_distributors(category);
CREATE INDEX IF NOT EXISTS idx_distributors_segment ON flv_distributors(segment);
CREATE INDEX IF NOT EXISTS idx_distributors_risk ON flv_distributors(risk_level);
CREATE INDEX IF NOT EXISTS idx_distributors_state ON flv_distributors(state_uf);

-- Tabela de Histórico de Alterações Societárias
CREATE TABLE IF NOT EXISTS flv_corporate_changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_cnpj TEXT NOT NULL,
    company_name TEXT,
    change_type TEXT CHECK(change_type IN ('diretoria', 'socio', 'administrador', 'capital_social', 'objeto_social', 'denominacao', 'sede')),
    change_subtype TEXT, -- Específico do tipo (ex: 'entrada', 'saída' para diretoria)
    old_value   TEXT,
    new_value   TEXT,
    change_date TEXT NOT NULL,
    source      TEXT, -- 'junta_comercial', 'diario_oficial', 'tribunal', 'receita_federal'
    source_url  TEXT,
    confidence_score REAL, -- Score de confiança na informação (0-1)
    processed   INTEGER DEFAULT 0, -- Flag para processamento
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_corp_changes_cnpj ON flv_corporate_changes(company_cnpj);
CREATE INDEX IF NOT EXISTS idx_corp_changes_type ON flv_corporate_changes(change_type);
CREATE INDEX IF NOT EXISTS idx_corp_changes_date ON flv_corporate_changes(change_date);
CREATE INDEX IF NOT EXISTS idx_corp_changes_processed ON flv_corporate_changes(processed);

-- Tabela de Monitoramento de Crescimento (GrowthRadar)
CREATE TABLE IF NOT EXISTS flv_growth_companies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    cnpj        TEXT UNIQUE,
    segment     TEXT, -- 'varejo_insumos', 'logistica', 'trading', 'processamento', 'tecnologia'
    growth_rate_12m REAL, -- Taxa de crescimento 12 meses
    growth_rate_24m REAL, -- Taxa de crescimento 24 meses
    revenue_current REAL,
    revenue_previous REAL,
    employee_growth_pct REAL,
    store_growth_pct REAL,
    market_expansion TEXT, -- JSON com novos mercados/polos detectados
    investment_round TEXT, -- Última rodada de investimento
    overtrading_risk BOOLEAN DEFAULT 0, -- Flag de risco de overtrading
    risk_reason   TEXT, -- Motivo do alerta de overtrading
    lat           REAL,
    lon           REAL,
    city          TEXT,
    state_uf      TEXT,
    detection_date TEXT, -- Data de detecção do crescimento acelerado
    status        TEXT DEFAULT 'monitorando' CHECK(status IN ('monitorando', 'alerta', 'estavel', 'declinio')),
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_growth_segment ON flv_growth_companies(segment);
CREATE INDEX IF NOT EXISTS idx_growth_rate ON flv_growth_companies(growth_rate_12m);
CREATE INDEX IF NOT EXISTS idx_growth_risk ON flv_growth_companies(overtrading_risk);
CREATE INDEX IF NOT EXISTS idx_growth_status ON flv_growth_companies(status);

-- Tabela de Cadeia de Suprimentos (Dependências)
CREATE TABLE IF NOT EXISTS flv_supply_chain (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_cnpj TEXT NOT NULL, -- Fornecedor
    supplier_name TEXT,
    client_cnpj   TEXT NOT NULL, -- Cliente
    client_name   TEXT,
    dependency_type TEXT CHECK(dependency_type IN ('critica', 'alta', 'media', 'baixa')),
    products_supplied TEXT, -- JSON array de produtos
    volume_monthly REAL, -- Volume mensal em toneladas/unidades
    supply_risk_score REAL, -- Score de risco (0-1)
    alternative_suppliers TEXT, -- JSON com fornecedores alternativos
    last_verified TEXT, -- Última verificação da dependência
    status        TEXT DEFAULT 'ativo',
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_supply_supplier ON flv_supply_chain(supplier_cnpj);
CREATE INDEX IF NOT EXISTS idx_supply_client ON flv_supply_chain(client_cnpj);
CREATE INDEX IF NOT EXISTS idx_supply_risk ON flv_supply_chain(supply_risk_score);

-- Tabela de Feeds de Notícias Globais (News Pulse)
CREATE TABLE IF NOT EXISTS flv_news_global (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT NOT NULL, -- 'reuters', 'bloomberg', 'bbc', 'al_jazeera', 'outro'
    source_region TEXT, -- 'americas', 'europe', 'asia', 'middle_east', 'africa'
    category    TEXT, -- 'commodities', 'clima', 'geopolitica', 'logistica', 'economia', 'tecnologia'
    title       TEXT NOT NULL,
    summary     TEXT,
    url         TEXT,
    published_at TEXT NOT NULL,
    sentiment   TEXT CHECK(sentiment IN ('positivo', 'negativo', 'neutro')),
    sentiment_score REAL, -- Score de -1 a 1
    keywords    TEXT, -- JSON array de keywords extraídas
    impact_regions TEXT, -- JSON array de regiões impactadas (códigos ISO)
    related_commodities TEXT, -- JSON array de commodities relacionadas
    relevance_score REAL, -- Score de relevância (0-1)
    processed   INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_news_source ON flv_news_global(source);
CREATE INDEX IF NOT EXISTS idx_news_category ON flv_news_global(category);
CREATE INDEX IF NOT EXISTS idx_news_date ON flv_news_global(published_at);
CREATE INDEX IF NOT EXISTS idx_news_sentiment ON flv_news_global(sentiment);
CREATE INDEX IF NOT EXISTS idx_news_relevance ON flv_news_global(relevance_score);

-- Tabela de Relatórios Soberanos (Ciclo 15 dias)
CREATE TABLE IF NOT EXISTS flv_sovereign_reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    report_date TEXT NOT NULL,
    report_type TEXT CHECK(report_type IN ('d-8', 'd+7')), -- Tipo de relatório
    report_period_start TEXT,
    report_period_end TEXT,
    
    -- Métricas de Stress de Mercado (D-8)
    stress_market_score REAL, -- Score geral de stress (0-100)
    companies_rj_entered INTEGER, -- Empresas que entraram em RJ
    companies_bankrupt INTEGER, -- Falências decretadas
    acquisitions_detected INTEGER, -- Aquisições detectadas
    asset_auctions_count INTEGER, -- Leilões de ativos
    
    -- Variações de Preço
    cepea_variation_pct REAL, -- Variação CEPEA
    ibge_variation_pct REAL, -- Variação IBGE
    conab_variation_pct REAL, -- Variação CONAB
    
    -- Análise Setorial
    sectors_in_crisis TEXT, -- JSON array de setores em crise
    sectors_growing TEXT, -- JSON array de setores em crescimento
    
    -- Sugestões Estratégicas (D+7)
    suggestions_json TEXT, -- JSON array com 3 sugestões práticas
    suggestions_confidence TEXT, -- JSON com scores de confiança
    
    -- Metadados
    generated_by  TEXT DEFAULT 'sistema', -- 'sistema' ou usuário
    is_auto_generated INTEGER DEFAULT 1,
    delivered      INTEGER DEFAULT 0, -- Se foi entregue ao usuário
    delivered_at   TEXT,
    
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sovereign_date ON flv_sovereign_reports(report_date);
CREATE INDEX IF NOT EXISTS idx_sovereign_type ON flv_sovereign_reports(report_type);
CREATE INDEX IF NOT EXISTS idx_sovereign_delivered ON flv_sovereign_reports(delivered);

-- Tabela de Mídias Sociais (Realidade de Campo)
CREATE TABLE IF NOT EXISTS flv_social_media (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    platform    TEXT CHECK(platform IN ('twitter', 'instagram', 'youtube', 'tiktok', 'facebook', 'outro')),
    author      TEXT,
    author_handle TEXT,
    content_type TEXT CHECK(content_type IN ('video', 'imagem', 'texto')),
    content_url  TEXT,
    content_text TEXT,
    published_at TEXT,
    lat          REAL, -- Geolocalização do post
    lon          REAL,
    location_name TEXT,
    
    -- Análise de Conteúdo
    category     TEXT CHECK(category IN ('praga', 'quebra_safra', 'recorde_produtividade', 'clima_extremo', 'protesto', 'logistica', 'outro')),
    severity     TEXT CHECK(severity IN ('baixa', 'media', 'alta', 'critica')),
    confidence_score REAL, -- Confiança na classificação
    related_culture TEXT, -- Cultura relacionada
    related_region TEXT, -- Região afetada
    
    -- Metadados
    verified     INTEGER DEFAULT 0, -- Se foi verificado por analista
    featured     INTEGER DEFAULT 0, -- Se deve ser destacado
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_social_platform ON flv_social_media(platform);
CREATE INDEX IF NOT EXISTS idx_social_category ON flv_social_media(category);
CREATE INDEX IF NOT EXISTS idx_social_date ON flv_social_media(published_at);
CREATE INDEX IF NOT EXISTS idx_social_featured ON flv_social_media(featured);

-- Tabela de Preços nas Gôndolas (Consumo Final)
CREATE TABLE IF NOT EXISTS flv_retail_prices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    product_category TEXT, -- 'hortifruti', 'graos', 'carnes', 'laticinios'
    retail_chain TEXT, -- 'carrefour', 'walmart', 'cencosud', 'grupo_mateus', 'atacadao', 'outro'
    store_city   TEXT,
    store_country TEXT, -- 'BR', 'AR', 'CL', 'PE', 'CO', etc.
    price_brl    REAL, -- Preço em reais
    price_local  REAL, -- Preço na moeda local
    local_currency TEXT, -- 'BRL', 'ARS', 'CLP', 'PEN', 'COP', etc.
    unit         TEXT, -- 'kg', 'unidade', 'pacote', etc.
    promotion    INTEGER DEFAULT 0, -- Se está em promoção
    collected_at TEXT, -- Data de coleta
    source       TEXT, -- 'web_scraping', 'api', 'manual'
    source_url   TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_retail_product ON flv_retail_prices(product_name);
CREATE INDEX IF NOT EXISTS idx_retail_chain ON flv_retail_prices(retail_chain);
CREATE INDEX IF NOT EXISTS idx_retail_country ON flv_retail_prices(store_country);
CREATE INDEX IF NOT EXISTS idx_retail_date ON flv_retail_prices(collected_at);

-- Tabela de Imagens de Satélite (Estrangulamento Logístico)
CREATE TABLE IF NOT EXISTS flv_satellite_imagery (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    image_type  TEXT CHECK(image_type IN ('porto', 'rodovia', 'hidrovia', 'terminal', 'armazem')),
    location_name TEXT,
    lat         REAL,
    lon         REAL,
    country     TEXT,
    
    -- Dados da Imagem
    capture_date TEXT,
    satellite   TEXT, -- 'sentinel-2', 'landsat', 'planet'
    resolution_m REAL, -- Resolução em metros
    image_url   TEXT,
    
    -- Análise
    analysis_type TEXT, -- 'congestionamento', 'estoque', 'atividade', 'anomalia'
    congestion_level REAL, -- Nível de congestionamento (0-1)
    vehicle_count INTEGER, -- Contagem de veículos (estimada)
    activity_status TEXT CHECK(activity_status IN ('normal', 'aumentada', 'reduzida', 'parada')),
    
    -- Metadados
    processed   INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_satellite_type ON flv_satellite_imagery(image_type);
CREATE INDEX IF NOT EXISTS idx_satellite_date ON flv_satellite_imagery(capture_date);
CREATE INDEX IF NOT EXISTS idx_satellite_country ON flv_satellite_imagery(country);
