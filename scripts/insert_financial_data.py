import sqlite3
from datetime import datetime, timedelta
import random

conn = sqlite3.connect('nia_flv.db')
cursor = conn.cursor()

# Criar tabela de dados financeiros e mercado de ações se não existir
cursor.execute('''
    CREATE TABLE IF NOT EXISTS flv_financial_health (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT NOT NULL,
        cnpj TEXT,
        ticker TEXT,
        country TEXT,
        sector TEXT,
        market_cap_usd REAL,
        revenue_usd REAL,
        net_income_usd REAL,
        debt_to_equity REAL,
        current_ratio REAL,
        roe_percent REAL,
        profit_margin REAL,
        stock_price REAL,
        price_change_30d REAL,
        price_change_ytd REAL,
        ceo_name TEXT,
        ceo_since DATE,
        ceo_changed_recently INTEGER DEFAULT 0,
        credit_rating TEXT,
        financial_health_score INTEGER,
        trend TEXT,
        last_update DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Criar tabela de instituições financeiras
cursor.execute('''
    CREATE TABLE IF NOT EXISTS flv_financial_institutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        country TEXT,
        type TEXT,
        assets_usd REAL,
        market_cap_usd REAL,
        credit_portfolio_usd REAL,
        npl_ratio REAL,
        roe_percent REAL,
        stock_ticker TEXT,
        stock_price REAL,
        price_change_ytd REAL,
        rating TEXT,
        exposure_agro_usd REAL,
        agro_loan_growth REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# Criar tabela de mudanças corporativas
cursor.execute('''
    CREATE TABLE IF NOT EXISTS flv_corporate_changes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_name TEXT,
        cnpj TEXT,
        country TEXT,
        change_type TEXT,
        old_value TEXT,
        new_value TEXT,
        change_date DATE,
        impact_level TEXT,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
print("✅ Tabelas criadas/atualizadas")

# Dados de empresas agrícolas da América do Sul
companies = [
    # ARGENTINA
    {
        'name': 'Cresud S.A.', 'ticker': 'CRESY', 'country': 'AR', 'sector': 'Agricultura',
        'market_cap': 850000000, 'revenue': 1200000000, 'net_income': 45000000,
        'debt_equity': 0.65, 'current_ratio': 1.25, 'roe': 8.5, 'profit_margin': 3.8,
        'price': 12.45, 'change_30d': -5.2, 'change_ytd': -12.8,
        'ceo': 'Alejandro Elsztain', 'ceo_since': '2019-03-15', 'ceo_changed': 0,
        'rating': 'BB-', 'health_score': 72, 'trend': 'stable'
    },
    {
        'name': 'Adecoagro S.A.', 'ticker': 'AGRO', 'country': 'AR', 'sector': 'Agricultura',
        'market_cap': 920000000, 'revenue': 980000000, 'net_income': 125000000,
        'debt_equity': 0.45, 'current_ratio': 1.45, 'roe': 15.2, 'profit_margin': 12.8,
        'price': 11.20, 'change_30d': 3.5, 'change_ytd': 8.4,
        'ceo': 'Mariano Bosch', 'ceo_since': '2021-06-01', 'ceo_changed': 0,
        'rating': 'BB', 'health_score': 78, 'trend': 'positive'
    },
    {
        'name': 'Bioceres Crop Solutions', 'ticker': 'BIOX', 'country': 'AR', 'sector': 'Biotecnologia',
        'market_cap': 420000000, 'revenue': 280000000, 'net_income': -15000000,
        'debt_equity': 0.35, 'current_ratio': 1.85, 'roe': -4.2, 'profit_margin': -5.4,
        'price': 8.75, 'change_30d': 12.8, 'change_ytd': 28.5,
        'ceo': 'Federico Trucco', 'ceo_since': '2023-01-10', 'ceo_changed': 1,
        'rating': 'B+', 'health_score': 65, 'trend': 'improving'
    },
    {
        'name': 'Grupo Los Grobo', 'ticker': 'GROBO', 'country': 'AR', 'sector': 'Trading',
        'market_cap': 380000000, 'revenue': 2100000000, 'net_income': 28000000,
        'debt_equity': 1.15, 'current_ratio': 0.95, 'roe': 9.8, 'profit_margin': 1.3,
        'price': 6.40, 'change_30d': -8.5, 'change_ytd': -22.4,
        'ceo': 'Gustavo Grobocopatel', 'ceo_since': '1984-01-01', 'ceo_changed': 0,
        'rating': 'B', 'health_score': 58, 'trend': 'negative'
    },
    
    # BRASIL
    {
        'name': 'SLC Agrícola S.A.', 'ticker': 'SLCE3', 'country': 'BR', 'sector': 'Agricultura',
        'market_cap': 5200000000, 'revenue': 4200000000, 'net_income': 850000000,
        'debt_equity': 0.55, 'current_ratio': 1.65, 'roe': 18.5, 'profit_margin': 20.2,
        'price': 52.30, 'change_30d': 7.8, 'change_ytd': 35.6,
        'ceo': 'Aurélio Pavinato', 'ceo_since': '2015-05-20', 'ceo_changed': 0,
        'rating': 'BBB-', 'health_score': 88, 'trend': 'positive'
    },
    {
        'name': 'São Martinho S.A.', 'ticker': 'SMTO3', 'country': 'BR', 'sector': 'Açúcar/Etanol',
        'market_cap': 7800000000, 'revenue': 5800000000, 'net_income': 920000000,
        'debt_equity': 0.42, 'current_ratio': 1.95, 'roe': 14.8, 'profit_margin': 15.9,
        'price': 42.85, 'change_30d': 4.2, 'change_ytd': 18.3,
        'ceo': 'Felipe Vicchiato', 'ceo_since': '2022-04-01', 'ceo_changed': 1,
        'rating': 'BBB', 'health_score': 85, 'trend': 'positive'
    },
    {
        'name': 'Raízen S.A.', 'ticker': 'RAIZ4', 'country': 'BR', 'sector': 'Energia/Bioenergia',
        'market_cap': 28000000000, 'revenue': 52000000000, 'net_income': 1850000000,
        'debt_equity': 1.25, 'current_ratio': 1.15, 'roe': 12.5, 'profit_margin': 3.6,
        'price': 4.25, 'change_30d': -2.1, 'change_ytd': -5.8,
        'ceo': 'Ricardo Mussa', 'ceo_since': '2021-09-01', 'ceo_changed': 0,
        'rating': 'BB+', 'health_score': 76, 'trend': 'stable'
    },
    {
        'name': '3tentos Agroindustrial', 'ticker': 'TTEN3', 'country': 'BR', 'sector': 'Varejo Insumos',
        'market_cap': 3200000000, 'revenue': 8900000000, 'net_income': 285000000,
        'debt_equity': 0.85, 'current_ratio': 1.35, 'roe': 16.8, 'profit_margin': 3.2,
        'price': 18.40, 'change_30d': 15.2, 'change_ytd': 42.8,
        'ceo': 'Ricardo de Abreu', 'ceo_since': '2024-01-15', 'ceo_changed': 1,
        'rating': 'BB+', 'health_score': 82, 'trend': 'positive'
    },
    {
        'name': 'Lavoro Ltd.', 'ticker': 'LVRO', 'country': 'BR', 'sector': 'Distribuição',
        'market_cap': 1200000000, 'revenue': 3200000000, 'net_income': -45000000,
        'debt_equity': 0.95, 'current_ratio': 1.05, 'roe': -4.5, 'profit_margin': -1.4,
        'price': 5.85, 'change_30d': -12.5, 'change_ytd': -35.2,
        'ceo': 'Ruy Cunha', 'ceo_since': '2022-03-01', 'ceo_changed': 0,
        'rating': 'B+', 'health_score': 62, 'trend': 'negative'
    },
    {
        'name': 'BrasilAgro', 'ticker': 'AGRO3', 'country': 'BR', 'sector': 'Agricultura',
        'market_cap': 4500000000, 'revenue': 2100000000, 'net_income': 620000000,
        'debt_equity': 0.25, 'current_ratio': 2.15, 'roe': 16.2, 'profit_margin': 29.5,
        'price': 32.80, 'change_30d': 2.8, 'change_ytd': 12.4,
        'ceo': 'André Guerreiro', 'ceo_since': '2018-07-01', 'ceo_changed': 0,
        'rating': 'BBB', 'health_score': 86, 'trend': 'positive'
    },
    {
        'name': 'Agrogalaxy', 'ticker': 'AGXY3', 'country': 'BR', 'sector': 'Varejo Insumos',
        'market_cap': 850000000, 'revenue': 4200000000, 'net_income': 45000000,
        'debt_equity': 1.45, 'current_ratio': 0.95, 'roe': 5.8, 'profit_margin': 1.1,
        'price': 3.25, 'change_30d': -18.5, 'change_ytd': -48.2,
        'ceo': 'Fábio Pires', 'ceo_since': '2023-11-01', 'ceo_changed': 1,
        'rating': 'B', 'health_score': 52, 'trend': 'negative'
    },
    {
        'name': 'Horácio Quaglio', 'ticker': 'HQCP3', 'country': 'BR', 'sector': 'Citrus',
        'market_cap': 1800000000, 'revenue': 1200000000, 'net_income': 145000000,
        'debt_equity': 0.35, 'current_ratio': 1.75, 'roe': 9.5, 'profit_margin': 12.1,
        'price': 28.50, 'change_30d': 5.2, 'change_ytd': 15.8,
        'ceo': 'José Renato Quaglio', 'ceo_since': '2010-01-01', 'ceo_changed': 0,
        'rating': 'BB+', 'health_score': 80, 'trend': 'stable'
    },
    {
        'name': 'Terra Santa Agro', 'ticker': 'LAND3', 'country': 'BR', 'sector': 'Agricultura',
        'market_cap': 950000000, 'revenue': 680000000, 'net_income': 125000000,
        'debt_equity': 0.55, 'current_ratio': 1.45, 'roe': 15.8, 'profit_margin': 18.4,
        'price': 11.20, 'change_30d': 8.5, 'change_ytd': 28.6,
        'ceo': 'Marcelo Ferraz', 'ceo_since': '2020-06-15', 'ceo_changed': 0,
        'rating': 'BB', 'health_score': 77, 'trend': 'positive'
    },
    {
        'name': 'Guararapes', 'ticker': 'GUAR3', 'country': 'BR', 'sector': 'Algodão',
        'market_cap': 650000000, 'revenue': 850000000, 'net_income': 28000000,
        'debt_equity': 0.85, 'current_ratio': 1.15, 'roe': 5.2, 'profit_margin': 3.3,
        'price': 8.45, 'change_30d': -4.2, 'change_ytd': -15.6,
        'ceo': 'Nelson Almeida', 'ceo_since': '2024-02-01', 'ceo_changed': 1,
        'rating': 'B+', 'health_score': 64, 'trend': 'stable'
    },
    
    # CHILE
    {
        'name': 'Sociedad Química y Minera', 'ticker': 'SQM', 'country': 'CL', 'sector': 'Fertilizantes',
        'market_cap': 15200000000, 'revenue': 10500000000, 'net_income': 2850000000,
        'debt_equity': 0.55, 'current_ratio': 1.85, 'roe': 28.5, 'profit_margin': 27.1,
        'price': 52.30, 'change_30d': -3.5, 'change_ytd': -18.2,
        'ceo': 'Ricardo Ramos', 'ceo_since': '2018-03-01', 'ceo_changed': 0,
        'rating': 'BBB+', 'health_score': 92, 'trend': 'stable'
    },
    {
        'name': 'Empresas AquaChile', 'ticker': 'AQUACHILE', 'country': 'CL', 'sector': 'Piscicultura',
        'market_cap': 850000000, 'revenue': 1200000000, 'net_income': -28000000,
        'debt_equity': 0.75, 'current_ratio': 1.25, 'roe': -3.8, 'profit_margin': -2.3,
        'price': 28.50, 'change_30d': -8.5, 'change_ytd': -22.4,
        'ceo': 'Sady Delgado', 'ceo_since': '2023-07-01', 'ceo_changed': 1,
        'rating': 'BB-', 'health_score': 61, 'trend': 'negative'
    },
    
    # COLOMBIA
    {
        'name': 'Grupo Nutresa', 'ticker': 'NUTRESA', 'country': 'CO', 'sector': 'Alimentos',
        'market_cap': 8200000000, 'revenue': 4200000000, 'net_income': 420000000,
        'debt_equity': 0.35, 'current_ratio': 1.95, 'roe': 14.2, 'profit_margin': 10.0,
        'price': 18.25, 'change_30d': 1.8, 'change_ytd': 5.4,
        'ceo': 'Carlos Enrique', 'ceo_since': '2022-01-01', 'ceo_changed': 0,
        'rating': 'BBB', 'health_score': 85, 'trend': 'stable'
    },
    {
        'name': 'Grupo Argos', 'ticker': 'GRUPOARGOS', 'country': 'CO', 'sector': 'Diversificado',
        'market_cap': 3200000000, 'revenue': 2800000000, 'net_income': 185000000,
        'debt_equity': 0.95, 'current_ratio': 1.15, 'roe': 8.5, 'profit_margin': 6.6,
        'price': 12.80, 'change_30d': -2.5, 'change_ytd': -8.4,
        'ceo': 'Jorge Mario Velásquez', 'ceo_since': '2024-03-01', 'ceo_changed': 1,
        'rating': 'BB+', 'health_score': 71, 'trend': 'stable'
    },
    
    # URUGUAI
    {
        'name': 'Perez Companc', 'ticker': 'PECOM', 'country': 'UY', 'sector': 'Energia/Agricultura',
        'market_cap': 1800000000, 'revenue': 2200000000, 'net_income': 145000000,
        'debt_equity': 0.65, 'current_ratio': 1.45, 'roe': 9.8, 'profit_margin': 6.6,
        'price': 32.40, 'change_30d': 3.2, 'change_ytd': 8.5,
        'ceo': 'Luis Perez Companc', 'ceo_since': '1990-01-01', 'ceo_changed': 0,
        'rating': 'BB', 'health_score': 76, 'trend': 'stable'
    },
    
    # PARAGUAI
    {
        'name': 'Grupo Cartes', 'ticker': 'CARTES', 'country': 'PY', 'sector': 'Diversificado',
        'market_cap': 2800000000, 'revenue': 3200000000, 'net_income': 285000000,
        'debt_equity': 0.55, 'current_ratio': 1.55, 'roe': 12.5, 'profit_margin': 8.9,
        'price': 45.80, 'change_30d': 5.8, 'change_ytd': 15.2,
        'ceo': 'Horacio Cartes Jr.', 'ceo_since': '2023-06-01', 'ceo_changed': 1,
        'rating': 'BB+', 'health_score': 79, 'trend': 'positive'
    },
    
    # PERU
    {
        'name': 'Alicorp', 'ticker': 'ALICORP1', 'country': 'PE', 'sector': 'Alimentos',
        'market_cap': 1800000000, 'revenue': 2800000000, 'net_income': 125000000,
        'debt_equity': 0.85, 'current_ratio': 1.25, 'roe': 8.2, 'profit_margin': 4.5,
        'price': 3.85, 'change_30d': -1.2, 'change_ytd': -3.5,
        'ceo': 'Eduardo Hochschild', 'ceo_since': '2021-04-01', 'ceo_changed': 0,
        'rating': 'BB', 'health_score': 73, 'trend': 'stable'
    },
    
    # MÉXICO (América Latina)
    {
        'name': 'Grupo México', 'ticker': 'GMEXICOB', 'country': 'MX', 'sector': 'Diversificado',
        'market_cap': 35000000000, 'revenue': 14000000000, 'net_income': 2850000000,
        'debt_equity': 0.65, 'current_ratio': 1.65, 'roe': 12.8, 'profit_margin': 20.4,
        'price': 85.60, 'change_30d': 4.2, 'change_ytd': 12.8,
        'ceo': 'Germán Larrea', 'ceo_since': '1994-01-01', 'ceo_changed': 0,
        'rating': 'BBB+', 'health_score': 89, 'trend': 'positive'
    },
    {
        'name': 'Archer Daniels Midland', 'ticker': 'ADM', 'country': 'US', 'sector': 'Trading',
        'market_cap': 28000000000, 'revenue': 85000000000, 'net_income': 2340000000,
        'debt_equity': 0.45, 'current_ratio': 1.55, 'roe': 12.5, 'profit_margin': 2.8,
        'price': 52.40, 'change_30d': -8.5, 'change_ytd': -22.4,
        'ceo': 'Juan Luciano', 'ceo_since': '2015-01-01', 'ceo_changed': 0,
        'rating': 'A-', 'health_score': 88, 'trend': 'stable'
    },
    {
        'name': 'Bunge Global', 'ticker': 'BG', 'country': 'US', 'sector': 'Trading',
        'market_cap': 14000000000, 'revenue': 54000000000, 'net_income': 1420000000,
        'debt_equity': 0.65, 'current_ratio': 1.35, 'roe': 14.2, 'profit_margin': 2.6,
        'price': 92.80, 'change_30d': 3.5, 'change_ytd': 5.8,
        'ceo': 'Greg Heckman', 'ceo_since': '2019-01-01', 'ceo_changed': 0,
        'rating': 'BBB+', 'health_score': 84, 'trend': 'positive'
    },
]

print(f"Inserindo {len(companies)} empresas...")

for comp in companies:
    cursor.execute('''
        INSERT INTO flv_financial_health 
        (company_name, ticker, country, sector, market_cap_usd, revenue_usd, net_income_usd,
         debt_to_equity, current_ratio, roe_percent, profit_margin, stock_price,
         price_change_30d, price_change_ytd, ceo_name, ceo_since, ceo_changed_recently,
         credit_rating, financial_health_score, trend, last_update)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        comp['name'], comp['ticker'], comp['country'], comp['sector'], 
        comp['market_cap'], comp['revenue'], comp['net_income'],
        comp['debt_equity'], comp['current_ratio'], comp['roe'], comp['profit_margin'],
        comp['price'], comp['change_30d'], comp['change_ytd'],
        comp['ceo'], comp['ceo_since'], comp['ceo_changed'],
        comp['rating'], comp['health_score'], comp['trend'],
        datetime.now().strftime('%Y-%m-%d')
    ))

conn.commit()
print(f"✅ {len(companies)} empresas inseridas")

# Instituições financeiras
print("\nInserindo instituições financeiras...")

banks = [
    {
        'name': 'Itaú Unibanco', 'country': 'BR', 'type': 'Banco Comercial',
        'assets': 450000000000, 'market_cap': 52000000000, 'credit_portfolio': 220000000000,
        'npl': 2.8, 'roe': 18.5, 'ticker': 'ITUB4', 'price': 32.50, 'change_ytd': 8.5,
        'rating': 'BBB+', 'exposure_agro': 85000000000, 'agro_growth': 12.5
    },
    {
        'name': 'Banco do Brasil', 'country': 'BR', 'type': 'Banco Público',
        'assets': 420000000000, 'market_cap': 28000000000, 'credit_portfolio': 185000000000,
        'npl': 3.2, 'roe': 15.2, 'ticker': 'BBAS3', 'price': 28.40, 'change_ytd': 15.8,
        'rating': 'BBB', 'exposure_agro': 185000000000, 'agro_growth': 8.5
    },
    {
        'name': 'Bradesco', 'country': 'BR', 'type': 'Banco Comercial',
        'assets': 380000000000, 'market_cap': 32000000000, 'credit_portfolio': 165000000000,
        'npl': 3.5, 'roe': 12.8, 'ticker': 'BBDC4', 'price': 14.25, 'change_ytd': -2.5,
        'rating': 'BBB', 'exposure_agro': 62000000000, 'agro_growth': 6.8
    },
    {
        'name': 'Rabobank Brasil', 'country': 'BR', 'type': 'Banco Cooperativo',
        'assets': 45000000000, 'market_cap': 8500000000, 'credit_portfolio': 28000000000,
        'npl': 1.8, 'roe': 14.5, 'ticker': 'RABOB', 'price': 125.00, 'change_ytd': 12.5,
        'rating': 'A-', 'exposure_agro': 25000000000, 'agro_growth': 18.5
    },
    {
        'name': 'Santander Brasil', 'country': 'BR', 'type': 'Banco Comercial',
        'assets': 320000000000, 'market_cap': 38000000000, 'credit_portfolio': 125000000000,
        'npl': 4.2, 'roe': 11.5, 'ticker': 'SANB11', 'price': 28.50, 'change_ytd': 5.2,
        'rating': 'BBB', 'exposure_agro': 35000000000, 'agro_growth': 9.2
    },
    {
        'name': 'Banco de Crédito BCP', 'country': 'PE', 'type': 'Banco Comercial',
        'assets': 52000000000, 'market_cap': 12500000000, 'credit_portfolio': 32000000000,
        'npl': 5.8, 'roe': 12.5, 'ticker': 'CREDITC1', 'price': 45.80, 'change_ytd': -5.2,
        'rating': 'BB+', 'exposure_agro': 8500000000, 'agro_growth': 15.5
    },
    {
        'name': 'Banco de Chile', 'country': 'CL', 'type': 'Banco Comercial',
        'assets': 68000000000, 'market_cap': 8500000000, 'credit_portfolio': 42000000000,
        'npl': 2.5, 'roe': 14.2, 'ticker': 'CHILE', 'price': 85.40, 'change_ytd': 3.8,
        'rating': 'A-', 'exposure_agro': 6500000000, 'agro_growth': 8.5
    },
    {
        'name': 'Banco Galicia', 'country': 'AR', 'type': 'Banco Comercial',
        'assets': 18000000000, 'market_cap': 3200000000, 'credit_portfolio': 8500000000,
        'npl': 4.5, 'roe': 8.5, 'ticker': 'GFG', 'price': 1250.00, 'change_ytd': -22.5,
        'rating': 'B+', 'exposure_agro': 2800000000, 'agro_growth': 25.5
    },
    {
        'name': 'Banco Itaú Argentina', 'country': 'AR', 'type': 'Banco Comercial',
        'assets': 8500000000, 'market_cap': 1850000000, 'credit_portfolio': 4200000000,
        'npl': 5.2, 'roe': 6.5, 'ticker': 'ITA', 'price': 680.00, 'change_ytd': -18.5,
        'rating': 'B+', 'exposure_agro': 1500000000, 'agro_growth': 18.5
    },
    {
        'name': 'Grupo Aval', 'country': 'CO', 'type': 'Holding Financeira',
        'assets': 85000000000, 'market_cap': 4200000000, 'credit_portfolio': 52000000000,
        'npl': 6.8, 'roe': 9.5, 'ticker': 'AVAL', 'price': 520.00, 'change_ytd': -8.5,
        'rating': 'BB', 'exposure_agro': 12500000000, 'agro_growth': 12.5
    },
]

for bank in banks:
    cursor.execute('''
        INSERT INTO flv_financial_institutions
        (name, country, type, assets_usd, market_cap_usd, credit_portfolio_usd, npl_ratio,
         roe_percent, stock_ticker, stock_price, price_change_ytd, rating, exposure_agro_usd, agro_loan_growth)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        bank['name'], bank['country'], bank['type'], bank['assets'], bank['market_cap'],
        bank['credit_portfolio'], bank['npl'], bank['roe'], bank['ticker'], bank['price'],
        bank['change_ytd'], bank['rating'], bank['exposure_agro'], bank['agro_growth']
    ))

conn.commit()
print(f"✅ {len(banks)} instituições financeiras inseridas")

# Mudanças corporativas recentes
print("\nInserindo mudanças corporativas...")

changes = [
    {
        'company': 'Bioceres Crop Solutions', 'country': 'AR', 'type': 'CEO',
        'old': 'Eduardo Kourany', 'new': 'Federico Trucco', 'date': '2023-01-10',
        'impact': 'alto', 'desc': 'Troca estratégica para foco em biotecnologia'
    },
    {
        'company': 'São Martinho S.A.', 'country': 'BR', 'type': 'CEO',
        'old': 'Lucas Araujo', 'new': 'Felipe Vicchiato', 'date': '2022-04-01',
        'impact': 'medio', 'desc': 'Renovação da gestão executiva'
    },
    {
        'company': '3tentos Agroindustrial', 'country': 'BR', 'type': 'CEO',
        'old': 'João Carlos', 'new': 'Ricardo de Abreu', 'date': '2024-01-15',
        'impact': 'alto', 'desc': 'Nova liderança para expansão nacional'
    },
    {
        'company': 'Agrogalaxy', 'country': 'BR', 'type': 'CEO',
        'old': 'André Skortz', 'new': 'Fábio Pires', 'date': '2023-11-01',
        'impact': 'alto', 'desc': 'Troca para reestruturação financeira'
    },
    {
        'company': 'Guararapes', 'country': 'BR', 'type': 'CEO',
        'old': 'Antônio Silva', 'new': 'Nelson Almeida', 'date': '2024-02-01',
        'impact': 'medio', 'desc': 'Nova gestão para diversificação'
    },
    {
        'company': 'Empresas AquaChile', 'country': 'CL', 'type': 'CEO',
        'old': 'Roberto Izquierdo', 'new': 'Sady Delgado', 'date': '2023-07-01',
        'impact': 'alto', 'desc': 'Mudança em momento de crise setorial'
    },
    {
        'company': 'Grupo Argos', 'country': 'CO', 'type': 'CEO',
        'old': 'José Contreras', 'new': 'Jorge Mario Velásquez', 'date': '2024-03-01',
        'impact': 'medio', 'desc': 'Sucessão planejada na presidência'
    },
    {
        'company': 'Grupo Cartes', 'country': 'PY', 'type': 'CEO',
        'old': 'Horacio Cartes Sr.', 'new': 'Horacio Cartes Jr.', 'date': '2023-06-01',
        'impact': 'alto', 'desc': 'Transição geracional na família fundadora'
    },
]

for change in changes:
    cursor.execute('''
        INSERT INTO flv_corporate_changes
        (company_name, country, change_type, old_value, new_value, change_date, impact_level, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        change['company'], change['country'], change['type'], change['old'],
        change['new'], change['date'], change['impact'], change['desc']
    ))

conn.commit()
print(f"✅ {len(changes)} mudanças corporativas registradas")

print("\n" + "="*60)
print("RESUMO DO SISTEMA FINANCEIRO")
print("="*60)

cursor.execute("SELECT COUNT(*) FROM flv_financial_health")
print(f"Empresas: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM flv_financial_institutions")
print(f"Instituições financeiras: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM flv_corporate_changes")
print(f"Mudanças corporativas: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM flv_financial_health WHERE ceo_changed_recently = 1")
print(f"Trocas de CEO recentes: {cursor.fetchone()[0]}")

cursor.execute("SELECT country, COUNT(*) FROM flv_financial_health GROUP BY country")
print("\nDistribuição por país:")
for country, count in cursor.fetchall():
    print(f"  {country}: {count} empresas")

cursor.execute("""
    SELECT company_name, price_change_ytd FROM flv_financial_health 
    ORDER BY price_change_ytd DESC LIMIT 5
""")
print("\n📈 TOP 5 - Maiores Altas no Ano:")
for name, change in cursor.fetchall():
    print(f"  {name}: +{change:.1f}%")

cursor.execute("""
    SELECT company_name, price_change_ytd FROM flv_financial_health 
    ORDER BY price_change_ytd ASC LIMIT 5
""")
print("\n📉 TOP 5 - Maiores Baixas no Ano:")
for name, change in cursor.fetchall():
    print(f"  {name}: {change:.1f}%")

cursor.execute("""
    SELECT name, agro_loan_growth FROM flv_financial_institutions 
    ORDER BY agro_loan_growth DESC LIMIT 3
""")
print("\n🏦 Bancos com Maior Crescimento em Agronegócio:")
for name, growth in cursor.fetchall():
    print(f"  {name}: +{growth:.1f}%")

conn.close()
print("\n✅ Sistema financeiro completo!")
