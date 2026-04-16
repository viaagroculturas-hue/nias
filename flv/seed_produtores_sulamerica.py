"""
Seed de Produtores da América do Sul
Insere produtores de Argentina, Paraguai, Uruguai, Chile, Colômbia e Peru
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')

# Produtores da América do Sul
PRODUTORES_SULAMERICA = [
    # ARGENTINA
    {
        'name': 'Estancia La Esperanza',
        'city': 'Rosario',
        'state_uf': 'AR',
        'lat': -32.9442,
        'lon': -60.6505,
        'products': ['SOJA', 'TRIGO', 'MILHO'],
        'volumes': {'SOJA': '50000 ton/ano', 'TRIGO': '30000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Agroindustrias Pampas S.A.',
        'city': 'Buenos Aires',
        'state_uf': 'AR',
        'lat': -34.6037,
        'lon': -58.3816,
        'products': ['CARNE_BOVINA', 'SOJA', 'CEVADA'],
        'volumes': {'CARNE_BOVINA': '20000 ton/ano', 'SOJA': '40000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Finca San Jorge',
        'city': 'Córdoba',
        'state_uf': 'AR',
        'lat': -31.4201,
        'lon': -64.1888,
        'products': ['TRIGO', 'CEVADA', 'AVEIA'],
        'volumes': {'TRIGO': '25000 ton/ano', 'CEVADA': '15000 ton/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Bodegas Mendoza',
        'city': 'Mendoza',
        'state_uf': 'AR',
        'lat': -32.8895,
        'lon': -68.8458,
        'products': ['UVA', 'VINHO', 'AZEITONA'],
        'volumes': {'UVA': '30000 ton/ano', 'VINHO': '15000000 L/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Estancia El Dorado',
        'city': 'Santa Fe',
        'state_uf': 'AR',
        'lat': -31.6107,
        'lon': -60.6973,
        'products': ['SOJA', 'MILHO', 'GIRASSOL'],
        'volumes': {'SOJA': '60000 ton/ano', 'MILHO': '45000 ton/ano'},
        'market_channel': 'Exportação'
    },
    # PARAGUAI
    {
        'name': 'Agropecuaria Guarani S.A.',
        'city': 'Asunción',
        'state_uf': 'PY',
        'lat': -25.2637,
        'lon': -57.5759,
        'products': ['SOJA', 'MILHO', 'ALGODAO'],
        'volumes': {'SOJA': '80000 ton/ano', 'MILHO': '50000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Finca Paraguaya',
        'city': 'Ciudad del Este',
        'state_uf': 'PY',
        'lat': -25.5097,
        'lon': -54.6111,
        'products': ['SOJA', 'CANA_DE_ACUCAR', 'MANDIOCA'],
        'volumes': {'SOJA': '40000 ton/ano', 'CANA_DE_ACUCAR': '200000 ton/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Estancia San Miguel',
        'city': 'Encarnación',
        'state_uf': 'PY',
        'lat': -27.3306,
        'lon': -55.8667,
        'products': ['SOJA', 'TRIGO', 'ERVILHA'],
        'volumes': {'SOJA': '35000 ton/ano', 'TRIGO': '20000 ton/ano'},
        'market_channel': 'Mercado Local'
    },
    # URUGUAI
    {
        'name': 'Estancia La Aurora',
        'city': 'Montevidéu',
        'state_uf': 'UY',
        'lat': -34.9011,
        'lon': -56.1645,
        'products': ['CARNE_BOVINA', 'LA', 'SOJA'],
        'volumes': {'CARNE_BOVINA': '15000 ton/ano', 'SOJA': '25000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Agroindustrias del Plata',
        'city': 'Paysandú',
        'state_uf': 'UY',
        'lat': -32.3214,
        'lon': -58.0756,
        'products': ['SOJA', 'TRIGO', 'CEVADA'],
        'volumes': {'SOJA': '45000 ton/ano', 'TRIGO': '30000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Finca San José',
        'city': 'Salto',
        'state_uf': 'UY',
        'lat': -31.3833,
        'lon': -57.9667,
        'products': ['CITRICOS', 'ARROZ', 'SOJA'],
        'volumes': {'CITRICOS': '20000 ton/ano', 'ARROZ': '15000 ton/ano'},
        'market_channel': 'CEASA'
    },
    # CHILE
    {
        'name': 'Viñas del Valle',
        'city': 'Santiago',
        'state_uf': 'CL',
        'lat': -33.4489,
        'lon': -70.6693,
        'products': ['UVA', 'VINHO', 'MAÇA'],
        'volumes': {'UVA': '40000 ton/ano', 'VINHO': '25000000 L/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Agrícola del Norte',
        'city': 'Antofagasta',
        'state_uf': 'CL',
        'lat': -23.6504,
        'lon': -70.3950,
        'products': ['TOMATE', 'PIMENTAO', 'UVA'],
        'volumes': {'TOMATE': '25000 ton/ano', 'UVA': '30000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Frutas del Sur',
        'city': 'Valparaíso',
        'state_uf': 'CL',
        'lat': -33.0472,
        'lon': -71.6127,
        'products': ['UVA', 'MAÇA', 'PERA'],
        'volumes': {'UVA': '35000 ton/ano', 'MAÇA': '20000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Pesquera Chile',
        'city': 'Concepción',
        'state_uf': 'CL',
        'lat': -36.8270,
        'lon': -73.0503,
        'products': ['SALMAO', 'TRUTA', 'MARISCOS'],
        'volumes': {'SALMAO': '50000 ton/ano'},
        'market_channel': 'Exportação'
    },
    # COLÔMBIA
    {
        'name': 'Café del Eje Cafetero',
        'city': 'Medellín',
        'state_uf': 'CO',
        'lat': 6.2476,
        'lon': -75.5658,
        'products': ['CAFE', 'BANANA', 'CACAU'],
        'volumes': {'CAFE': '25000 ton/ano', 'BANANA': '40000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Flores de Colombia',
        'city': 'Bogotá',
        'state_uf': 'CO',
        'lat': 4.7110,
        'lon': -74.0721,
        'products': ['ROSAS', 'CRAVOS', 'ORQUIDEAS'],
        'volumes': {'ROSAS': '50000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Agroindustria Andina',
        'city': 'Cali',
        'state_uf': 'CO',
        'lat': 3.4516,
        'lon': -76.5320,
        'products': ['CANA_DE_ACUCAR', 'ALGODAO', 'SOJA'],
        'volumes': {'CANA_DE_ACUCAR': '300000 ton/ano'},
        'market_channel': 'CEASA'
    },
    # PERU
    {
        'name': 'Agroexportadora Peru',
        'city': 'Lima',
        'state_uf': 'PE',
        'lat': -12.0464,
        'lon': -77.0428,
        'products': ['ASPARGOS', 'UVA', 'MANGA'],
        'volumes': {'ASPARGOS': '15000 ton/ano', 'UVA': '25000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Quinua Andina',
        'city': 'Cusco',
        'state_uf': 'PE',
        'lat': -13.1631,
        'lon': -72.5450,
        'products': ['QUINUA', 'MACA', 'AMARANTO'],
        'volumes': {'QUINUA': '8000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Café del Valle Sagrado',
        'city': 'Arequipa',
        'state_uf': 'PE',
        'lat': -16.4090,
        'lon': -71.5375,
        'products': ['CAFE', 'CACAU', 'BANANA'],
        'volumes': {'CAFE': '12000 ton/ano', 'CACAU': '8000 ton/ano'},
        'market_channel': 'Mercado Local'
    },
    {
        'name': 'Pesquera del Pacífico',
        'city': 'Trujillo',
        'state_uf': 'PE',
        'lat': -8.1150,
        'lon': -79.0300,
        'products': ['ANCHOVETA', 'ATUM', 'CAMARAO'],
        'volumes': {'ANCHOVETA': '80000 ton/ano'},
        'market_channel': 'Exportação'
    },
    # EQUADOR
    {
        'name': 'Bananas del Ecuador',
        'city': 'Guayaquil',
        'state_uf': 'EC',
        'lat': -2.1894,
        'lon': -79.8891,
        'products': ['BANANA', 'CACAU', 'PALMA'],
        'volumes': {'BANANA': '60000 ton/ano', 'CACAU': '15000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Rosas de los Andes',
        'city': 'Quito',
        'state_uf': 'EC',
        'lat': -0.1807,
        'lon': -78.4678,
        'products': ['ROSAS', 'BROCOLIS', 'ALFACE'],
        'volumes': {'ROSAS': '30000 ton/ano'},
        'market_channel': 'Exportação'
    },
    # BOLÍVIA
    {
        'name': 'Soja del Oriente',
        'city': 'Santa Cruz de la Sierra',
        'state_uf': 'BO',
        'lat': -17.7833,
        'lon': -63.1821,
        'products': ['SOJA', 'MILHO', 'GIRASSOL'],
        'volumes': {'SOJA': '35000 ton/ano', 'MILHO': '25000 ton/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Quinua Real',
        'city': 'La Paz',
        'state_uf': 'BO',
        'lat': -16.5000,
        'lon': -68.1500,
        'products': ['QUINUA', 'AMARANTO', 'CANAUI'],
        'volumes': {'QUINUA': '10000 ton/ano'},
        'market_channel': 'Exportação'
    },
]

def seed_produtores_sulamerica():
    """Insere produtores da América do Sul no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    
    for prod in PRODUTORES_SULAMERICA:
        try:
            # Verificar se já existe
            cursor.execute('SELECT id FROM flv_producers WHERE name = ?', (prod['name'],))
            existing = cursor.fetchone()
            
            data = {
                'name': prod['name'],
                'city': prod['city'],
                'state_uf': prod['state_uf'],
                'lat': prod['lat'],
                'lon': prod['lon'],
                'products': json.dumps(prod['products']),
                'production_volume': json.dumps(prod.get('volumes', {})),
                'market_channel': prod.get('market_channel', 'CEASA'),
                'status': 'ativo'
            }
            
            if existing:
                cursor.execute('''
                    UPDATE flv_producers SET
                        city = ?, state_uf = ?, lat = ?, lon = ?, products = ?,
                        production_volume = ?, market_channel = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                ''', (data['city'], data['state_uf'], data['lat'], data['lon'], 
                      data['products'], data['production_volume'], 
                      data['market_channel'], existing[0]))
                updated += 1
            else:
                cursor.execute('''
                    INSERT INTO flv_producers
                    (name, city, state_uf, lat, lon, products, production_volume, 
                     market_channel, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (data['name'], data['city'], data['state_uf'], data['lat'], 
                      data['lon'], data['products'], data['production_volume'],
                      data['market_channel'], data['status']))
                inserted += 1
                
        except Exception as e:
            print(f"Erro ao inserir {prod['name']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✓ Produtores Sul-Americanos inseridos: {inserted}")
    print(f"✓ Produtores Sul-Americanos atualizados: {updated}")
    print(f"✓ Total: {inserted + updated}")

if __name__ == '__main__':
    seed_produtores_sulamerica()
