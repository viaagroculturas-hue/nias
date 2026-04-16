"""
Seed de Produtores em Recuperação Judicial - Rio de Janeiro
Insere produtores do RJ em situação de recuperação judicial
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')

# Produtores do RJ em Recuperação Judicial - dados representativos
PRODUTORES_RJ_RJ = [
    {
        'company_name': 'Agropecuária Vale do Paraíba S.A.',
        'cnpj': '12.345.678/0001-90',
        'process_number': '0001234-12.2023.8.19.0001',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'em_recuperacao',
        'city': 'Campos dos Goytacazes',
        'lat': -21.7542,
        'lon': -41.3244,
        'products': ['CANA_DE_ACUCAR', 'MILHO', 'SOJA', 'GADO_BOVINO'],
        'volumes': {'CANA_DE_ACUCAR': '50000 ton/ano', 'MILHO': '5000 ton/ano', 'SOJA': '3000 ton/ano'},
        'annual_revenue': 45000000.00,
        'employees': 120,
        'debts_total': 78000000.00,
        'entry_date': '2023-03-15'
    },
    {
        'company_name': 'Fazendas Reunidas do Norte Fluminense Ltda.',
        'cnpj': '23.456.789/0001-01',
        'process_number': '0002345-23.2024.8.19.0002',
        'court': '2ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'em_recuperacao',
        'city': 'Itaperuna',
        'lat': -21.2033,
        'lon': -41.8901,
        'products': ['LEITE', 'GADO_LEITEIRO', 'MILHO', 'SILAGEM'],
        'volumes': {'LEITE': '50000 L/dia', 'GADO_LEITEIRO': '2000 cabeças'},
        'annual_revenue': 28000000.00,
        'employees': 85,
        'debts_total': 42000000.00,
        'entry_date': '2024-01-20'
    },
    {
        'company_name': 'Citricola do Rio Bonito S.A.',
        'cnpj': '34.567.890/0001-12',
        'process_number': '0003456-34.2023.8.19.0003',
        'court': '3ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'recuperacao_aprovada',
        'city': 'Rio Bonito',
        'lat': -22.7097,
        'lon': -42.6093,
        'products': ['LARANJA', 'LIMAO', 'MEXERICA', 'SUCO_CONCENTRADO'],
        'volumes': {'LARANJA': '15000 ton/ano', 'LIMAO': '5000 ton/ano'},
        'annual_revenue': 32000000.00,
        'employees': 95,
        'debts_total': 55000000.00,
        'entry_date': '2023-06-10'
    },
    {
        'company_name': 'Cooperativa Agroindustrial de Petrópolis',
        'cnpj': '45.678.901/0001-23',
        'process_number': '0004567-45.2024.8.19.0004',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'em_recuperacao',
        'city': 'Petrópolis',
        'lat': -22.5054,
        'lon': -43.1786,
        'products': ['ALFACE', 'COUVE', 'BROCOLIS', 'AGRIAO', 'ESPINAFRE'],
        'volumes': {'ALFACE': '200 ton/mes', 'COUVE': '150 ton/mes', 'BROCOLIS': '100 ton/mes'},
        'annual_revenue': 15000000.00,
        'employees': 45,
        'debts_total': 22000000.00,
        'entry_date': '2024-02-28'
    },
    {
        'company_name': 'Hortifruti Seropédica Ltda.',
        'cnpj': '56.789.012/0001-34',
        'process_number': '0005678-56.2023.8.19.0005',
        'court': '2ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'reorganizado',
        'city': 'Seropédica',
        'lat': -22.7439,
        'lon': -43.7079,
        'products': ['TOMATE', 'PIMENTAO', 'BERINGELA', 'PEPINO', 'ABOBRINHA'],
        'volumes': {'TOMATE': '300 ton/mes', 'PIMENTAO': '200 ton/mes'},
        'annual_revenue': 18000000.00,
        'employees': 60,
        'debts_total': 28000000.00,
        'entry_date': '2023-09-05'
    },
    {
        'company_name': 'Fruticultura Bom Jesus Ltda.',
        'cnpj': '67.890.123/0001-45',
        'process_number': '0006789-67.2024.8.19.0006',
        'court': '3ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'em_recuperacao',
        'city': 'Bom Jesus do Itabapoana',
        'lat': -21.1406,
        'lon': -41.6797,
        'products': ['MANGA', 'GOIABA', 'MARACUJA', 'COCO'],
        'volumes': {'MANGA': '8000 ton/ano', 'GOIABA': '3000 ton/ano', 'MARACUJA': '2000 ton/ano'},
        'annual_revenue': 12000000.00,
        'employees': 35,
        'debts_total': 18000000.00,
        'entry_date': '2024-04-12'
    },
    {
        'company_name': 'Avícola Nova Iguaçu S.A.',
        'cnpj': '78.901.234/0001-56',
        'process_number': '0007890-78.2023.8.19.0007',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'falencia',
        'city': 'Nova Iguaçu',
        'lat': -22.7595,
        'lon': -43.4496,
        'products': ['FRANGO', 'OVOS', 'RAÇÃO_ANIMAL'],
        'volumes': {'FRANGO': '50000 unidades/semana', 'OVOS': '100000 unidades/dia'},
        'annual_revenue': 35000000.00,
        'employees': 150,
        'debts_total': 65000000.00,
        'entry_date': '2023-11-18'
    },
    {
        'company_name': 'Pescados do Litoral Norte Ltda.',
        'cnpj': '89.012.345/0001-67',
        'process_number': '0008901-89.2024.8.19.0008',
        'court': '2ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'em_recuperacao',
        'city': 'Cabo Frio',
        'lat': -22.8794,
        'lon': -42.0186,
        'products': ['CAMARAO', 'PEIXE', 'OSTRA', 'MARISCO'],
        'volumes': {'CAMARAO': '50 ton/mes', 'PEIXE': '30 ton/mes'},
        'annual_revenue': 8500000.00,
        'employees': 28,
        'debts_total': 12000000.00,
        'entry_date': '2024-05-20'
    },
    {
        'company_name': 'Cafeicultura Serrana do Rio Ltda.',
        'cnpj': '90.123.456/0001-78',
        'process_number': '0009012-90.2023.8.19.0009',
        'court': '3ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'recuperacao_aprovada',
        'city': 'Vassouras',
        'lat': -22.5374,
        'lon': -43.6625,
        'products': ['CAFE_ARABICA', 'CAFE_ROBUSTA', 'CAFE_TORRADO'],
        'volumes': {'CAFE_ARABICA': '2000 sacas/ano', 'CAFE_ROBUSTA': '1000 sacas/ano'},
        'annual_revenue': 9500000.00,
        'employees': 22,
        'debts_total': 14000000.00,
        'entry_date': '2023-07-30'
    },
    {
        'company_name': 'Agroindustrial de Teresópolis S.A.',
        'cnpj': '01.234.567/0001-89',
        'process_number': '0000123-01.2024.8.19.0010',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro',
        'judicial_status': 'em_recuperacao',
        'city': 'Teresópolis',
        'lat': -22.4165,
        'lon': -42.9757,
        'products': ['MORANGO', 'AMORA', 'FRAMBOESA', 'GELEIAS'],
        'volumes': {'MORANGO': '100 ton/ano', 'AMORA': '50 ton/ano', 'FRAMBOESA': '30 ton/ano'},
        'annual_revenue': 7200000.00,
        'employees': 18,
        'debts_total': 9500000.00,
        'entry_date': '2024-03-08'
    },
]

def seed_producers_rj():
    """Insere produtores em RJ no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Garantir que tabela existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flv_producers_rj (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            cnpj TEXT UNIQUE,
            process_number TEXT,
            court TEXT,
            judicial_status TEXT DEFAULT 'em_recuperacao',
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT NOT NULL,
            state_uf TEXT NOT NULL DEFAULT 'RJ',
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            products TEXT NOT NULL,
            production_volume TEXT,
            annual_revenue REAL,
            employees INTEGER,
            debts_total REAL,
            recovery_plan TEXT,
            entry_date TEXT,
            status TEXT DEFAULT 'ativo',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    
    inserted = 0
    updated = 0
    
    for prod in PRODUTORES_RJ_RJ:
        try:
            # Verificar se já existe
            cursor.execute('SELECT id FROM flv_producers_rj WHERE cnpj = ?', (prod['cnpj'],))
            existing = cursor.fetchone()
            
            data = {
                'company_name': prod['company_name'],
                'cnpj': prod['cnpj'],
                'process_number': prod.get('process_number', ''),
                'court': prod.get('court', ''),
                'judicial_status': prod.get('judicial_status', 'em_recuperacao'),
                'city': prod['city'],
                'state_uf': 'RJ',
                'lat': prod['lat'],
                'lon': prod['lon'],
                'products': json.dumps(prod['products']),
                'production_volume': json.dumps(prod.get('volumes', {})),
                'annual_revenue': prod.get('annual_revenue', 0),
                'employees': prod.get('employees', 0),
                'debts_total': prod.get('debts_total', 0),
                'entry_date': prod.get('entry_date', ''),
                'status': 'ativo'
            }
            
            if existing:
                # Update
                cursor.execute('''
                    UPDATE flv_producers_rj SET
                        company_name = ?, process_number = ?, court = ?, judicial_status = ?,
                        city = ?, lat = ?, lon = ?, products = ?, production_volume = ?,
                        annual_revenue = ?, employees = ?, debts_total = ?, entry_date = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                ''', (data['company_name'], data['process_number'], data['court'], 
                      data['judicial_status'], data['city'], data['lat'], data['lon'],
                      data['products'], data['production_volume'], data['annual_revenue'],
                      data['employees'], data['debts_total'], data['entry_date'], existing[0]))
                updated += 1
            else:
                # Insert
                cursor.execute('''
                    INSERT INTO flv_producers_rj
                    (company_name, cnpj, process_number, court, judicial_status, city, state_uf, 
                     lat, lon, products, production_volume, annual_revenue, employees, 
                     debts_total, entry_date, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (data['company_name'], data['cnpj'], data['process_number'], 
                      data['court'], data['judicial_status'], data['city'], data['state_uf'],
                      data['lat'], data['lon'], data['products'], data['production_volume'],
                      data['annual_revenue'], data['employees'], data['debts_total'],
                      data['entry_date'], data['status']))
                inserted += 1
                
        except Exception as e:
            print(f"Erro ao inserir {prod['company_name']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✓ Produtores RJ inseridos: {inserted}")
    print(f"✓ Produtores RJ atualizados: {updated}")
    print(f"✓ Total: {inserted + updated}")

if __name__ == '__main__':
    seed_producers_rj()
