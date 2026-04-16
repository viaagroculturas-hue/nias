"""
Seed de Produtores do Rio de Janeiro
Insere produtores reais do RJ no banco de dados
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')

# Produtores do Rio de Janeiro - dados representativos
PRODUTORES_RJ = [
    {
        'name': 'Fazenda São João - Nova Iguaçu',
        'city': 'Nova Iguaçu',
        'lat': -22.7595,
        'lon': -43.4496,
        'products': ['TOMATE', 'ALFACE', 'COUVE', 'CHEIRO VERDE'],
        'volumes': {'TOMATE': '500 kg/mês', 'ALFACE': '300 kg/mês'},
        'market': 'CEASA'
    },
    {
        'name': 'Cooperativa Rural de Seropédica',
        'city': 'Seropédica',
        'lat': -22.7439,
        'lon': -43.7079,
        'products': ['MAMÃO', 'BANANA', 'MARACUJÁ', 'ABACAXI'],
        'volumes': {'MAMÃO': '2 ton/mês', 'BANANA': '3 ton/mês'},
        'market': 'Misto'
    },
    {
        'name': 'Sítio Boa Vista - Itaguaí',
        'city': 'Itaguaí',
        'lat': -22.8637,
        'lon': -43.7761,
        'products': ['PIMENTÃO', 'BERINGELA', 'ABOBRINHA', 'PEPINO'],
        'volumes': {'PIMENTÃO': '800 kg/mês', 'BERINGELA': '600 kg/mês'},
        'market': 'Direto'
    },
    {
        'name': 'Fazenda Vale Verde - Paracambi',
        'city': 'Paracambi',
        'lat': -22.6106,
        'lon': -43.7064,
        'products': ['MILHO VERDE', 'QUIABO', 'VAGEM', 'BETERRABA'],
        'volumes': {'MILHO VERDE': '1.5 ton/mês', 'QUIABO': '400 kg/mês'},
        'market': 'CEASA'
    },
    {
        'name': 'Cooperflora - Petrópolis',
        'city': 'Petrópolis',
        'lat': -22.5054,
        'lon': -43.1786,
        'products': ['ALFACE', 'RÚCULA', 'AGRIÃO', 'ESPINAFRE', 'ACELGA'],
        'volumes': {'ALFACE': '1 ton/mês', 'RÚCULA': '500 kg/mês'},
        'market': 'Mercado Local',
        'certifications': 'Orgânico'
    },
    {
        'name': 'Sítio Santa Luzia - Vassouras',
        'city': 'Vassouras',
        'lat': -22.5374,
        'lon': -43.6625,
        'products': ['LARANJA', 'LIMAO', 'TANGERINA'],
        'volumes': {'LARANJA': '5 ton/mês', 'LIMAO': '2 ton/mês'},
        'market': 'CEASA'
    },
    {
        'name': 'Fazenda Recanto - Miguel Pereira',
        'city': 'Miguel Pereira',
        'lat': -22.4554,
        'lon': -43.4686,
        'products': ['MORANGO', 'AMORA', 'FRAMBOESA'],
        'volumes': {'MORANGO': '300 kg/mês'},
        'market': 'Direto',
        'certifications': 'Orgânico'
    },
    {
        'name': 'Associação de Produtores de Rio Bonito',
        'city': 'Rio Bonito',
        'lat': -22.7097,
        'lon': -42.6093,
        'products': ['BATATA', 'CENOURA', 'NABO', 'RABANETE'],
        'volumes': {'BATATA': '2 ton/mês', 'CENOURA': '1.5 ton/mês'},
        'market': 'CEASA'
    },
    {
        'name': 'Fazenda São Pedro - Cachoeiras de Macacu',
        'city': 'Cachoeiras de Macacu',
        'lat': -22.4631,
        'lon': -42.6512,
        'products': ['CAFÉ', 'BANANA', 'ABACATE'],
        'volumes': {'CAFÉ': '10 ton/ano', 'BANANA': '2 ton/mês'},
        'market': 'Exportação'
    },
    {
        'name': 'Sítio Nossa Senhora - São José do Vale do Rio Preto',
        'city': 'São José do Vale do Rio Preto',
        'lat': -22.2486,
        'lon': -42.9189,
        'products': ['LEITE', 'QUEIJO', 'IOGURTE', 'MANTEIGA'],
        'volumes': {'LEITE': '500 L/dia'},
        'market': 'Direto'
    },
    {
        'name': 'Cooperativa Agroecológica - Teresópolis',
        'city': 'Teresópolis',
        'lat': -22.4165,
        'lon': -42.9757,
        'products': ['ALFACE', 'COUVE', 'BROCOLIS', 'REPOLHO', 'CEBOLA'],
        'volumes': {'ALFACE': '800 kg/mês', 'COUVE': '600 kg/mês'},
        'market': 'Mercado Local',
        'certifications': 'Orgânico'
    },
    {
        'name': 'Fazenda Vista Alegre - Bom Jesus do Itabapoana',
        'city': 'Bom Jesus do Itabapoana',
        'lat': -21.1406,
        'lon': -41.6797,
        'products': ['CANA DE AÇÚCAR', 'MANDIOCA', 'MILHO'],
        'volumes': {'CANA DE AÇÚCAR': '100 ton/ano'},
        'market': 'Direto'
    },
    {
        'name': 'Sítio Bela Vista - Cambuci',
        'city': 'Cambuci',
        'lat': -21.5733,
        'lon': -41.9146,
        'products': ['GOIABA', 'ACEROLA', 'CAJÚ', 'MANGA'],
        'volumes': {'GOIABA': '1.5 ton/mês', 'ACEROLA': '800 kg/mês'},
        'market': 'CEASA'
    },
    {
        'name': 'Fazenda Santa Maria - Itaperuna',
        'city': 'Itaperuna',
        'lat': -21.2033,
        'lon': -41.8901,
        'products': ['OVOS', 'FRANGO', 'MILHO', 'SOJA'],
        'volumes': {'OVOS': '1000/dia', 'FRANGO': '500 kg/semana'},
        'market': 'Misto'
    },
    {
        'name': 'Cooperativa dos Horticultores - Campos dos Goytacazes',
        'city': 'Campos dos Goytacazes',
        'lat': -21.7542,
        'lon': -41.3244,
        'products': ['TOMATE', 'PIMENTÃO', 'COUVE-FLOR', 'REPOLHO', 'CENOURA'],
        'volumes': {'TOMATE': '5 ton/mês', 'PIMENTÃO': '3 ton/mês'},
        'market': 'CEASA'
    },
]

def seed_producers():
    """Insere produtores no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Garantir que tabela existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS flv_producers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            document TEXT UNIQUE,
            phone TEXT,
            email TEXT,
            address TEXT,
            city TEXT NOT NULL,
            state_uf TEXT NOT NULL DEFAULT 'RJ',
            lat REAL NOT NULL,
            lon REAL NOT NULL,
            products TEXT NOT NULL,
            production_volume TEXT,
            certifications TEXT,
            market_channel TEXT,
            status TEXT DEFAULT 'ativo',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    ''')
    
    inserted = 0
    updated = 0
    
    for prod in PRODUTORES_RJ:
        try:
            # Verificar se já existe
            cursor.execute('SELECT id FROM flv_producers WHERE name = ?', (prod['name'],))
            existing = cursor.fetchone()
            
            data = {
                'name': prod['name'],
                'city': prod['city'],
                'state_uf': 'RJ',
                'lat': prod['lat'],
                'lon': prod['lon'],
                'products': json.dumps(prod['products']),
                'production_volume': json.dumps(prod.get('volumes', {})),
                'certifications': prod.get('certifications', ''),
                'market_channel': prod.get('market', 'CEASA'),
                'status': 'ativo'
            }
            
            if existing:
                # Update
                cursor.execute('''
                    UPDATE flv_producers SET
                        city = ?, lat = ?, lon = ?, products = ?,
                        production_volume = ?, certifications = ?, market_channel = ?,
                        updated_at = datetime('now')
                    WHERE id = ?
                ''', (data['city'], data['lat'], data['lon'], data['products'],
                      data['production_volume'], data['certifications'], 
                      data['market_channel'], existing[0]))
                updated += 1
            else:
                # Insert
                cursor.execute('''
                    INSERT INTO flv_producers
                    (name, city, state_uf, lat, lon, products, production_volume, 
                     certifications, market_channel, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (data['name'], data['city'], data['state_uf'], data['lat'], 
                      data['lon'], data['products'], data['production_volume'],
                      data['certifications'], data['market_channel'], data['status']))
                inserted += 1
                
        except Exception as e:
            print(f"Erro ao inserir {prod['name']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"✓ Produtores inseridos: {inserted}")
    print(f"✓ Produtores atualizados: {updated}")
    print(f"✓ Total: {inserted + updated}")

if __name__ == '__main__':
    seed_producers()
