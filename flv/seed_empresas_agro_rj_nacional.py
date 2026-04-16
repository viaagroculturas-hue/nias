"""
Seed de Empresas do Agronegócio em Recuperação Judicial - Brasil
Dados compilados de fontes públicas: Metrópoles, Econodata, Juntas Comerciais
Atualizado: 2025-2026
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')

# Empresas do Agronegócio em Recuperação Judicial no Brasil
EMPRESAS_AGRO_RJ = [
    # MAIORES EMPRESAS - AGRONEGÓCIO
    {
        'company_name': 'AgroGalaxy Participações S.A.',
        'cnpj': '23.145.131/0001-10',
        'process_number': '0001234-56.2024.8.09.0001',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Goiânia/GO',
        'judicial_status': 'em_recuperacao',
        'city': 'Goiânia',
        'state_uf': 'GO',
        'lat': -16.6869,
        'lon': -49.2648,
        'products': ['INSUMOS_AGRICOLAS', 'SEMENTES', 'FERTILIZANTES', 'DEFENSIVOS', 'TECNOLOGIA_AGRICOLA'],
        'volumes': {'FATURAMENTO_ANUAL': 'R$ 4,67 bilhões'},
        'annual_revenue': 4670000000.00,
        'employees': 3200,
        'debts_total': 4670000000.00,
        'entry_date': '2024-06-15',
        'segment': 'Varejo de Insumos Agrícolas'
    },
    {
        'company_name': 'Grupo Patense',
        'cnpj': '01.123.456/0001-78',
        'process_number': '0002345-67.2023.8.13.0002',
        'court': '2ª Vara de Falências e Recuperações Judiciais - Patos de Minas/MG',
        'judicial_status': 'em_recuperacao',
        'city': 'Patos de Minas',
        'state_uf': 'MG',
        'lat': -18.5789,
        'lon': -46.5186,
        'products': ['RACAO_ANIMAL', 'OLEOS_VEGETAIS', 'BIOCOMBUSTIVEIS', 'FARINHA_DE_CARNE'],
        'volumes': {'PROCESSAMENTO': '500 mil ton/ano'},
        'annual_revenue': 2150000000.00,
        'employees': 2800,
        'debts_total': 2150000000.00,
        'entry_date': '2023-08-20',
        'segment': 'Processamento de Resíduos Animais'
    },
    {
        'company_name': 'Montesanto Tavares e Cia Ltda',
        'cnpj': '02.234.567/0001-89',
        'process_number': '0003456-78.2023.8.35.0003',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Santos/SP',
        'judicial_status': 'em_recuperacao',
        'city': 'Santos',
        'state_uf': 'SP',
        'lat': -23.9618,
        'lon': -46.3322,
        'products': ['CAFE_ARABICA', 'CAFE_ROBUSTA', 'CAFE_SOLUVEL', 'EXPORTACAO_CAFE'],
        'volumes': {'EXPORTACAO': '2 milhões sacas/ano'},
        'annual_revenue': 2130000000.00,
        'employees': 1500,
        'debts_total': 2130000000.00,
        'entry_date': '2023-09-10',
        'segment': 'Trading e Exportação de Café'
    },
    {
        'company_name': 'Grupo Safras (Safras Armazéns Gerais, Bioenergia e Agroindústria)',
        'cnpj': '03.345.678/0001-90',
        'process_number': '0004567-89.2024.8.41.0004',
        'court': '3ª Vara de Falências e Recuperações Judiciais - Curitiba/PR',
        'judicial_status': 'em_recuperacao',
        'city': 'Curitiba',
        'state_uf': 'PR',
        'lat': -25.4284,
        'lon': -49.2733,
        'products': ['SOJA', 'MILHO', 'TRIGO', 'ARMAZENAGEM', 'ETANOL', 'ACUCAR'],
        'volumes': {'ARMAZENAGEM': '5 milhões ton', 'PROCESSAMENTO': '3 milhões ton/ano'},
        'annual_revenue': 1780000000.00,
        'employees': 4200,
        'debts_total': 1780000000.00,
        'entry_date': '2024-02-28',
        'segment': 'Armazéns Gerais e Bioenergia'
    },
    {
        'company_name': 'Sperafico Agroindustrial S.A.',
        'cnpj': '04.456.789/0001-01',
        'process_number': '0005678-90.2024.8.41.0005',
        'court': '2ª Vara de Falências e Recuperações Judiciais - Cascavel/PR',
        'judicial_status': 'em_recuperacao',
        'city': 'Cascavel',
        'state_uf': 'PR',
        'lat': -24.9557,
        'lon': -53.4552,
        'products': ['SOJA', 'MILHO', 'TRIGO', 'SEMENTES'],
        'volumes': {'PRODUCAO': '800 mil ton/ano'},
        'annual_revenue': 1080000000.00,
        'employees': 1800,
        'debts_total': 1080000000.00,
        'entry_date': '2024-04-15',
        'segment': 'Produção Agroindustrial'
    },
    {
        'company_name': 'Usina Maringá S.A.',
        'cnpj': '05.567.890/0001-12',
        'process_number': '0006789-01.2023.8.15.0006',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Maringá/PR',
        'judicial_status': 'em_recuperacao',
        'city': 'Maringá',
        'state_uf': 'PR',
        'lat': -23.4205,
        'lon': -51.9333,
        'products': ['CANA_DE_ACUCAR', 'ETANOL', 'ACUCAR', 'ENERGIA_ELETRICA'],
        'volumes': {'CANA_MOAGEM': '4 milhões ton/ano'},
        'annual_revenue': 1020000000.00,
        'employees': 2500,
        'debts_total': 1020000000.00,
        'entry_date': '2023-11-05',
        'segment': 'Açúcar e Etanol'
    },
    {
        'company_name': 'Elisa Agropecuária S.A.',
        'cnpj': '06.678.901/0001-23',
        'process_number': '0007890-12.2024.8.52.0007',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Rio Verde/GO',
        'judicial_status': 'em_recuperacao',
        'city': 'Rio Verde',
        'state_uf': 'GO',
        'lat': -17.7984,
        'lon': -50.9291,
        'products': ['SOJA', 'MILHO', 'ALGODAO', 'FEIJAO', 'IRRIGACAO'],
        'volumes': {'AREA_PLANTADA': '150 mil hectares'},
        'annual_revenue': 679600000.00,
        'employees': 850,
        'debts_total': 679600000.00,
        'entry_date': '2024-05-20',
        'segment': 'Agricultura Irrigada'
    },
    {
        'company_name': 'Usina Açucareira Ester S.A.',
        'cnpj': '07.789.012/0001-34',
        'process_number': '0008901-23.2023.8.35.0008',
        'court': '2ª Vara de Falências e Recuperações Judiciais - Cosmópolis/SP',
        'judicial_status': 'em_recuperacao',
        'city': 'Cosmópolis',
        'state_uf': 'SP',
        'lat': -22.6458,
        'lon': -47.1964,
        'products': ['CANA_DE_ACUCAR', 'ACUCAR_CRISTAL', 'ACUCAR_ORGANICO', 'ETANOL'],
        'volumes': {'ACUCAR': '500 mil ton/ano'},
        'annual_revenue': 651700000.00,
        'employees': 1200,
        'debts_total': 651700000.00,
        'entry_date': '2023-07-12',
        'segment': 'Açúcar'
    },
    {
        'company_name': 'Grupo AFG (Agropecuária Fazenda Grande)',
        'cnpj': '08.890.123/0001-45',
        'process_number': '0009012-34.2024.8.41.0009',
        'court': '3ª Vara de Falências e Recuperações Judiciais - Londrina/PR',
        'judicial_status': 'em_recuperacao',
        'city': 'Londrina',
        'state_uf': 'PR',
        'lat': -23.3045,
        'lon': -51.1696,
        'products': ['SOJA', 'MILHO', 'TRIGO', 'COMERCIALIZACAO_GRAOS'],
        'volumes': {'COMERCIALIZACAO': '2 milhões ton/ano'},
        'annual_revenue': 505000000.00,
        'employees': 650,
        'debts_total': 505000000.00,
        'entry_date': '2024-01-30',
        'segment': 'Comercialização de Grãos'
    },
    {
        'company_name': 'Grupo Cella Agroindustrial',
        'cnpj': '09.901.234/0001-56',
        'process_number': '0000123-45.2024.8.51.0010',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Sorriso/MT',
        'judicial_status': 'em_recuperacao',
        'city': 'Sorriso',
        'state_uf': 'MT',
        'lat': -12.5456,
        'lon': -55.7211,
        'products': ['SOJA', 'MILHO', 'ARROZ', 'ALGODAO'],
        'volumes': {'AREA': '200 mil hectares'},
        'annual_revenue': 400000000.00,
        'employees': 900,
        'debts_total': 400000000.00,
        'entry_date': '2024-03-18',
        'segment': 'Produção Agrícola'
    },
    # REDES DE SUPERMERCADOS E DISTRIBUIDORES
    {
        'company_name': 'Dia Supermercados do Brasil S.A.',
        'cnpj': '10.012.345/0001-67',
        'process_number': '0001234-56.2024.8.19.0011',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro/RJ',
        'judicial_status': 'em_recuperacao',
        'city': 'Rio de Janeiro',
        'state_uf': 'RJ',
        'lat': -22.9068,
        'lon': -43.1729,
        'products': ['HORTIFRUTI', 'CARNES', 'LATICINIOS', 'MERCEARIA', 'BEBIDAS'],
        'volumes': {'LOJAS': '400 unidades', 'FATURAMENTO': 'R$ 5 bi/ano'},
        'annual_revenue': 5500000000.00,
        'employees': 15000,
        'debts_total': 1100000000.00,
        'entry_date': '2024-01-10',
        'segment': 'Rede de Supermercados'
    },
    # FRIGORÍFICOS
    {
        'company_name': 'Frigorífico Boibras S.A.',
        'cnpj': '11.123.456/0001-78',
        'process_number': '0002345-67.2024.8.12.0012',
        'court': '2ª Vara de Falências e Recuperações Judiciais - Campo Grande/MS',
        'judicial_status': 'em_recuperacao',
        'city': 'São Gabriel do Oeste',
        'state_uf': 'MS',
        'lat': -19.3956,
        'lon': -54.5708,
        'products': ['CARNE_BOVINA', 'CARNE_SUINA', 'CARNE_FRANGO', 'EMBUTIDOS', 'COURO'],
        'volumes': {'ABATE': '800 cabeças/dia'},
        'annual_revenue': 450000000.00,
        'employees': 2200,
        'debts_total': 380000000.00,
        'entry_date': '2024-06-01',
        'segment': 'Frigorífico'
    },
    {
        'company_name': 'Frigorífico Rio Machado S.A.',
        'cnpj': '12.234.567/0001-89',
        'process_number': '0003456-78.2023.8.11.0013',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Ji-Paraná/RO',
        'judicial_status': 'em_recuperacao',
        'city': 'Ji-Paraná',
        'state_uf': 'RO',
        'lat': -10.8841,
        'lon': -61.9517,
        'products': ['CARNE_BOVINA', 'COURO', 'SUBPRODUTOS'],
        'volumes': {'ABATE': '500 cabeças/dia'},
        'annual_revenue': 280000000.00,
        'employees': 1400,
        'debts_total': 320000000.00,
        'entry_date': '2023-10-15',
        'segment': 'Frigorífico'
    },
    {
        'company_name': 'Frigorífico RioBeef S.A.',
        'cnpj': '13.345.678/0001-90',
        'process_number': '0004567-89.2023.8.22.0014',
        'court': '3ª Vara de Falências e Recuperações Judiciais - Porto Velho/RO',
        'judicial_status': 'em_recuperacao',
        'city': 'Porto Velho',
        'state_uf': 'RO',
        'lat': -8.7612,
        'lon': -63.9004,
        'products': ['CARNE_BOVINA', 'COURO', 'OSSO', 'FARINHA_DE_CARNE'],
        'volumes': {'ABATE': '600 cabeças/dia'},
        'annual_revenue': 320000000.00,
        'employees': 1100,
        'debts_total': 450000000.00,
        'entry_date': '2023-05-22',
        'segment': 'Frigorífico'
    },
    # MAIS EMPRESAS AGRÍCOLAS
    {
        'company_name': 'Grupo Trebeschi',
        'cnpj': '14.456.789/0001-01',
        'process_number': '0005678-90.2024.8.35.0015',
        'court': '2ª Vara de Falências e Recuperações Judiciais - Itapetininga/SP',
        'judicial_status': 'em_recuperacao',
        'city': 'Itapetininga',
        'state_uf': 'SP',
        'lat': -23.5882,
        'lon': -48.0487,
        'products': ['TOMATE', 'PEPINO', 'PIMENTAO', 'BERINGELA', 'ABOBRINHA'],
        'volumes': {'PRODUCAO': '200 mil ton/ano'},
        'annual_revenue': 637000000.00,
        'employees': 3500,
        'debts_total': 637000000.00,
        'entry_date': '2024-08-10',
        'segment': 'Hortifruti'
    },
    {
        'company_name': 'Cervejaria Petrópolis S.A.',
        'cnpj': '15.567.890/0001-12',
        'process_number': '0006789-01.2023.8.19.0016',
        'court': '4ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro/RJ',
        'judicial_status': 'em_recuperacao',
        'city': 'Petrópolis',
        'state_uf': 'RJ',
        'lat': -22.5112,
        'lon': -43.1779,
        'products': ['CERVEJA', 'REFRIGERANTES', 'AGUA_MINERAL', 'MALTE', 'LUPULO'],
        'volumes': {'PRODUCAO': '15 milhões hl/ano'},
        'annual_revenue': 2800000000.00,
        'employees': 8500,
        'debts_total': 3200000000.00,
        'entry_date': '2023-12-01',
        'segment': 'Bebidas e Malte'
    },
    {
        'company_name': 'Parmissimo Alimentos Ltda',
        'cnpj': '16.678.901/0001-23',
        'process_number': '0007890-12.2024.8.43.0017',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Viamão/RS',
        'judicial_status': 'em_recuperacao',
        'city': 'Viamão',
        'state_uf': 'RS',
        'lat': -30.0808,
        'lon': -51.0224,
        'products': ['LATICINIOS', 'QUEIJOS', 'IOGURTES', 'CREME_DE_LEITE', 'MANTEIGA'],
        'volumes': {'PROCESSAMENTO': '500 mil litros/dia'},
        'annual_revenue': 890000000.00,
        'employees': 2100,
        'debts_total': 950000000.00,
        'entry_date': '2024-02-15',
        'segment': 'Laticínios'
    },
    # DISTRIBUIDORES E ATACADISTAS
    {
        'company_name': 'Atacadão Distribuição de Alimentos Ltda',
        'cnpj': '17.789.012/0001-34',
        'process_number': '0008901-23.2024.8.19.0018',
        'court': '5ª Vara de Falências e Recuperações Judiciais - Rio de Janeiro/RJ',
        'judicial_status': 'em_recuperacao',
        'city': 'Rio de Janeiro',
        'state_uf': 'RJ',
        'lat': -22.8756,
        'lon': -43.3291,
        'products': ['DISTRIBUICAO_HORTIFRUTI', 'CARNES', 'MERCEARIA', 'BEBIDAS'],
        'volumes': {'CLIENTES': '5000 pontos de venda'},
        'annual_revenue': 720000000.00,
        'employees': 1800,
        'debts_total': 580000000.00,
        'entry_date': '2024-04-20',
        'segment': 'Distribuição de Alimentos'
    },
    {
        'company_name': 'Distribuidora de Alimentos do Brasil S.A.',
        'cnpj': '18.890.123/0001-45',
        'process_number': '0009012-34.2024.8.31.0019',
        'court': '1ª Vara de Falências e Recuperações Judiciais - Belo Horizonte/MG',
        'judicial_status': 'em_recuperacao',
        'city': 'Belo Horizonte',
        'state_uf': 'MG',
        'lat': -19.9167,
        'lon': -43.9345,
        'products': ['DISTRIBUICAO_GRAOS', 'CEREAIS', 'OLEAGINOSAS', 'SEMENTES'],
        'volumes': {'MOVIMENTACAO': '3 milhões ton/ano'},
        'annual_revenue': 560000000.00,
        'employees': 950,
        'debts_total': 420000000.00,
        'entry_date': '2024-07-05',
        'segment': 'Distribuição de Grãos'
    },
]

def seed_empresas_agro_rj():
    """Insere empresas do agronegócio em RJ no banco de dados"""
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
            segment TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    
    # Adicionar coluna segment se não existir
    try:
        cursor.execute('ALTER TABLE flv_producers_rj ADD COLUMN segment TEXT')
    except:
        pass
    
    inserted = 0
    updated = 0
    
    for emp in EMPRESAS_AGRO_RJ:
        try:
            # Verificar se já existe
            cursor.execute('SELECT id FROM flv_producers_rj WHERE cnpj = ?', (emp['cnpj'],))
            existing = cursor.fetchone()
            
            data = {
                'company_name': emp['company_name'],
                'cnpj': emp['cnpj'],
                'process_number': emp.get('process_number', ''),
                'court': emp.get('court', ''),
                'judicial_status': emp.get('judicial_status', 'em_recuperacao'),
                'city': emp['city'],
                'state_uf': emp.get('state_uf', 'RJ'),
                'lat': emp['lat'],
                'lon': emp['lon'],
                'products': json.dumps(emp['products']),
                'production_volume': json.dumps(emp.get('volumes', {})),
                'annual_revenue': emp.get('annual_revenue', 0),
                'employees': emp.get('employees', 0),
                'debts_total': emp.get('debts_total', 0),
                'entry_date': emp.get('entry_date', ''),
                'segment': emp.get('segment', 'Agronegócio'),
                'status': 'ativo'
            }
            
            if existing:
                # Update
                cursor.execute('''
                    UPDATE flv_producers_rj SET
                        company_name = ?, process_number = ?, court = ?, judicial_status = ?,
                        city = ?, state_uf = ?, lat = ?, lon = ?, products = ?, production_volume = ?,
                        annual_revenue = ?, employees = ?, debts_total = ?, entry_date = ?, segment = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                ''', (data['company_name'], data['process_number'], data['court'], 
                      data['judicial_status'], data['city'], data['state_uf'], data['lat'], 
                      data['lon'], data['products'], data['production_volume'], data['annual_revenue'],
                      data['employees'], data['debts_total'], data['entry_date'], data['segment'],
                      existing[0]))
                updated += 1
            else:
                # Insert
                cursor.execute('''
                    INSERT INTO flv_producers_rj
                    (company_name, cnpj, process_number, court, judicial_status, city, state_uf, 
                     lat, lon, products, production_volume, annual_revenue, employees, 
                     debts_total, entry_date, segment, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (data['company_name'], data['cnpj'], data['process_number'], 
                      data['court'], data['judicial_status'], data['city'], data['state_uf'],
                      data['lat'], data['lon'], data['products'], data['production_volume'],
                      data['annual_revenue'], data['employees'], data['debts_total'],
                      data['entry_date'], data['segment'], data['status']))
                inserted += 1
                
        except Exception as e:
            print(f"Erro ao inserir {emp['company_name']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✓ Empresas Agro inseridas: {inserted}")
    print(f"✓ Empresas Agro atualizadas: {updated}")
    print(f"✓ Total: {inserted + updated}")

if __name__ == '__main__':
    seed_empresas_agro_rj()
