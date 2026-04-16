"""
Seed de Produtores de Todas as Regiões do Brasil
Inserir produtores de todas as regiões e culturas
"""
import sqlite3
import os
import json

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'nia_flv.db')

# Produtores de todas as regiões do Brasil - por região e cultura
PRODUTORES_BRASIL = [
    # ═══════════════════════════════════════════════════════════════
    # REGIÃO NORTE
    # ═══════════════════════════════════════════════════════════════
    
    # SOJA - MT (norte)
    {
        'name': 'Fazenda São João - Sorriso',
        'city': 'Sorriso',
        'state_uf': 'MT',
        'lat': -12.5456,
        'lon': -55.7211,
        'products': ['SOJA', 'MILHO'],
        'volumes': {'SOJA': '50000 ton/ano', 'MILHO': '30000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Agropecuária Norte MT Ltda',
        'city': 'Sinop',
        'state_uf': 'MT',
        'lat': -11.8604,
        'lon': -55.5091,
        'products': ['SOJA', 'MILHO', 'ALGODÃO'],
        'volumes': {'SOJA': '80000 ton/ano', 'MILHO': '45000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # PARÁ - Soja/Grãos
    {
        'name': 'Fazenda Bela Vista - Santarém',
        'city': 'Santarém',
        'state_uf': 'PA',
        'lat': -2.4506,
        'lon': -54.7084,
        'products': ['SOJA', 'MILHO', 'ARROZ'],
        'volumes': {'SOJA': '45000 ton/ano', 'MILHO': '25000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # RONDÔNIA - Café/Cacau
    {
        'name': 'Cooperativa Café do Ouro',
        'city': 'Vilhena',
        'state_uf': 'RO',
        'lat': -12.7414,
        'lon': -60.1386,
        'products': ['CAFÉ', 'CACAU', 'PIMENTA'],
        'volumes': {'CAFÉ': '15000 sacas/ano', 'CACAU': '5000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # ACRE - Borracha/Frutas nativas
    {
        'name': 'Seringal Rio Branco',
        'city': 'Rio Branco',
        'state_uf': 'AC',
        'lat': -9.9749,
        'lon': -67.8243,
        'products': ['BORRACHA', 'CASTANHA', 'AÇAÍ'],
        'volumes': {'BORRACHA': '2000 ton/ano', 'CASTANHA': '1500 ton/ano'},
        'market_channel': 'Direto'
    },
    
    # AMAZONAS - Frutas nativas
    {
        'name': 'Cooperativa Amazonas Frutas',
        'city': 'Manaus',
        'state_uf': 'AM',
        'lat': -3.1190,
        'lon': -60.0217,
        'products': ['AÇAÍ', 'CUPUAÇU', 'BURITI'],
        'volumes': {'AÇAÍ': '10000 ton/ano', 'CUPUAÇU': '3000 ton/ano'},
        'market_channel': 'Mercado Local'
    },
    
    # TOCANTINS - Soja/Grãos
    {
        'name': 'Fazenda Boa Esperança - Gurupi',
        'city': 'Gurupi',
        'state_uf': 'TO',
        'lat': -11.7286,
        'lon': -49.0686,
        'products': ['SOJA', 'MILHO', 'SORGO'],
        'volumes': {'SOJA': '60000 ton/ano', 'MILHO': '35000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # AMAPA - Frutas
    {
        'name': 'Cooperativa Amapá Verde',
        'city': 'Macapá',
        'state_uf': 'AP',
        'lat': 0.0355,
        'lon': -51.0705,
        'products': ['COCO', 'MARACUJÁ', 'MELANCIA'],
        'volumes': {'COCO': '5000 ton/ano', 'MARACUJÁ': '2000 ton/ano'},
        'market_channel': 'Mercado Local'
    },
    
    # RORAIMA - Hortaliças
    {
        'name': 'Hortifruti Boa Vista',
        'city': 'Boa Vista',
        'state_uf': 'RR',
        'lat': 2.8197,
        'lon': -60.6733,
        'products': ['ALFACE', 'TOMATE', 'PEPINO'],
        'volumes': {'ALFACE': '500 ton/ano', 'TOMATE': '800 ton/ano'},
        'market_channel': 'Mercado Local'
    },
    
    # ═══════════════════════════════════════════════════════════════
    # REGIÃO NORDESTE
    # ═══════════════════════════════════════════════════════════════
    
    # BAHIA - Soja/Oeste
    {
        'name': 'Fazenda Oeste Bahia - Luís Eduardo Magalhães',
        'city': 'Luís Eduardo Magalhães',
        'state_uf': 'BA',
        'lat': -12.0925,
        'lon': -45.7828,
        'products': ['SOJA', 'MILHO', 'ALGODÃO'],
        'volumes': {'SOJA': '120000 ton/ano', 'MILHO': '80000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # BAHIA - Cacau
    {
        'name': 'Cooperativa Cacau Sul da Bahia',
        'city': 'Itabuna',
        'state_uf': 'BA',
        'lat': -14.7856,
        'lon': -39.2802,
        'products': ['CACAU', 'CAFÉ'],
        'volumes': {'CACAU': '25000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # PERNAMBUCO - Uva/VSF
    {
        'name': 'Cooperativa do Vale do São Francisco',
        'city': 'Petrolina',
        'state_uf': 'PE',
        'lat': -9.3988,
        'lon': -40.5021,
        'products': ['UVA', 'MANGA', 'GOIABA'],
        'volumes': {'UVA': '200000 ton/ano', 'MANGA': '150000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # CEARÁ - Melão
    {
        'name': 'Cooperativa de Melão do Ceará',
        'city': 'Juazeiro do Norte',
        'state_uf': 'CE',
        'lat': -7.2247,
        'lon': -39.3136,
        'products': ['MELÃO', 'MELANCIA'],
        'volumes': {'MELÃO': '80000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # RIO GRANDE DO NORTE - Frutas
    {
        'name': 'Fazenda Tropical RN',
        'city': 'Mossoró',
        'state_uf': 'RN',
        'lat': -5.1878,
        'lon': -37.3443,
        'products': ['MELÃO', 'CAJU', 'MARACUJÁ'],
        'volumes': {'MELÃO': '45000 ton/ano', 'CAJU': '30000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # PARAÍBA - Algodão
    {
        'name': 'Cooperativa Algodoeira da Paraíba',
        'city': 'Campina Grande',
        'state_uf': 'PB',
        'lat': -7.2290,
        'lon': -35.8808,
        'products': ['ALGODÃO', 'AMENDOIM', 'MILHO'],
        'volumes': {'ALGODÃO': '30000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # ALAGOAS - Cana-de-açúcar
    {
        'name': 'Usina Santa Clotilde',
        'city': 'Maceió',
        'state_uf': 'AL',
        'lat': -9.6659,
        'lon': -35.7350,
        'products': ['CANA-DE-AÇÚCAR', 'ETANOL'],
        'volumes': {'CANA-DE-AÇÚCAR': '500000 ton/ano'},
        'market_channel': 'Direto'
    },
    
    # SERGIPE - Laranja
    {
        'name': 'Cooperativa Citrus de Sergipe',
        'city': 'Aracaju',
        'state_uf': 'SE',
        'lat': -10.9472,
        'lon': -37.0731,
        'products': ['LARANJA', 'TANGERINA'],
        'volumes': {'LARANJA': '60000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # PIAUÍ - Soja
    {
        'name': 'Fazenda Matopiba Sul',
        'city': 'Bom Jesus',
        'state_uf': 'PI',
        'lat': -9.0733,
        'lon': -44.3583,
        'products': ['SOJA', 'MILHO'],
        'volumes': {'SOJA': '40000 ton/ano', 'MILHO': '25000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # MARANHÃO - Soja
    {
        'name': 'Agropecuária Maranhão Verde',
        'city': 'Balsas',
        'state_uf': 'MA',
        'lat': -7.5325,
        'lon': -46.0356,
        'products': ['SOJA', 'MILHO', 'ALGODÃO'],
        'volumes': {'SOJA': '70000 ton/ano', 'MILHO': '40000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # ═══════════════════════════════════════════════════════════════
    # REGIÃO CENTRO-OESTE
    # ═══════════════════════════════════════════════════════════════
    
    # MATO GROSSO - Soja (maior produtor)
    {
        'name': 'Fazenda Primavera - Sorriso',
        'city': 'Sorriso',
        'state_uf': 'MT',
        'lat': -12.5456,
        'lon': -55.7211,
        'products': ['SOJA', 'MILHO', 'ALGODÃO'],
        'volumes': {'SOJA': '200000 ton/ano', 'MILHO': '120000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Agroindustrial Campo Verde',
        'city': 'Campo Verde',
        'state_uf': 'MT',
        'lat': -15.5469,
        'lon': -55.1656,
        'products': ['SOJA', 'MILHO', 'TRIGO'],
        'volumes': {'SOJA': '150000 ton/ano', 'MILHO': '90000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # GOIÁS - Soja/Cana
    {
        'name': 'Fazenda Rio Verde',
        'city': 'Rio Verde',
        'state_uf': 'GO',
        'lat': -17.7984,
        'lon': -50.9291,
        'products': ['SOJA', 'MILHO', 'SORGO'],
        'volumes': {'SOJA': '180000 ton/ano', 'MILHO': '100000 ton/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Usina São Martinho',
        'city': 'Goiânia',
        'state_uf': 'GO',
        'lat': -16.6869,
        'lon': -49.2648,
        'products': ['CANA-DE-AÇÚCAR', 'ETANOL', 'AÇÚCAR'],
        'volumes': {'CANA-DE-AÇÚCAR': '800000 ton/ano'},
        'market_channel': 'Direto'
    },
    
    # DISTRITO FEDERAL - Hortaliças
    {
        'name': 'Cooperplan - Planaltina',
        'city': 'Planaltina',
        'state_uf': 'DF',
        'lat': -15.4522,
        'lon': -47.6090,
        'products': ['ALFACE', 'COUVE', 'BROCOLIS', 'CENOURA'],
        'volumes': {'ALFACE': '15000 ton/ano', 'COUVE': '8000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # MATO GROSSO DO SUL - Soja/Boi
    {
        'name': 'Fazenda MS Agro',
        'city': 'Dourados',
        'state_uf': 'MS',
        'lat': -22.2231,
        'lon': -54.8120,
        'products': ['SOJA', 'MILHO', 'BOI GORDO'],
        'volumes': {'SOJA': '100000 ton/ano', 'BOI GORDO': '50000 cabeças/ano'},
        'market_channel': 'CEASA'
    },
    
    # ═══════════════════════════════════════════════════════════════
    # REGIÃO SUDESTE
    # ═══════════════════════════════════════════════════════════════
    
    # SÃO PAULO - Cana/Citrus
    {
        'name': 'Usina Raízen',
        'city': 'Piracicaba',
        'state_uf': 'SP',
        'lat': -22.7343,
        'lon': -47.6481,
        'products': ['CANA-DE-AÇÚCAR', 'ETANOL', 'AÇÚCAR'],
        'volumes': {'CANA-DE-AÇÚCAR': '1200000 ton/ano'},
        'market_channel': 'Direto'
    },
    {
        'name': 'Cooperativa Citrus São Paulo',
        'city': 'Bebedouro',
        'state_uf': 'SP',
        'lat': -20.9496,
        'lon': -48.4791,
        'products': ['LARANJA', 'LIMAO', 'TANGERINA'],
        'volumes': {'LARANJA': '300000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # SÃO PAULO - Hortifruti
    {
        'name': 'Cooperflora - Holambra',
        'city': 'Holambra',
        'state_uf': 'SP',
        'lat': -22.6413,
        'lon': -47.0485,
        'products': ['ALFACE', 'COUVE', 'BROCOLIS', 'ESPINAFRE'],
        'volumes': {'ALFACE': '25000 ton/ano', 'COUVE': '15000 ton/ano'},
        'market_channel': 'CEAGESP'
    },
    
    # MINAS GERAIS - Café/Leite
    {
        'name': 'Cooperativa Café Sul de Minas',
        'city': 'Poços de Caldas',
        'state_uf': 'MG',
        'lat': -21.7854,
        'lon': -46.5617,
        'products': ['CAFÉ', 'LEITE', 'QUEIJO'],
        'volumes': {'CAFÉ': '50000 sacas/ano', 'LEITE': '100000 litros/dia'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Fazenda Leite Verde - Uberlândia',
        'city': 'Uberlândia',
        'state_uf': 'MG',
        'lat': -18.9186,
        'lon': -48.2772,
        'products': ['LEITE', 'QUEIJO', 'IOGURTE'],
        'volumes': {'LEITE': '80000 litros/dia'},
        'market_channel': 'CEASA'
    },
    
    # ESPÍRITO SANTO - Café
    {
        'name': 'Cooperativa Café do Espírito Santo',
        'city': 'Linhares',
        'state_uf': 'ES',
        'lat': -19.3958,
        'lon': -40.0724,
        'products': ['CAFÉ', 'CACAU'],
        'volumes': {'CAFÉ': '30000 sacas/ano', 'CACAU': '8000 ton/ano'},
        'market_channel': 'Exportação'
    },
    
    # RIO DE JANEIRO - Leite/Hortifruti
    {
        'name': 'Fazenda Vale do Paraíba - Petrópolis',
        'city': 'Petrópolis',
        'state_uf': 'RJ',
        'lat': -22.5054,
        'lon': -43.1786,
        'products': ['LEITE', 'HORTALIÇAS', 'MORANGO'],
        'volumes': {'LEITE': '50000 litros/dia', 'MORANGO': '2000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # ═══════════════════════════════════════════════════════════════
    # REGIÃO SUL
    # ═══════════════════════════════════════════════════════════════
    
    # PARANÁ - Soja
    {
        'name': 'Cooperativa Agrária - Londrina',
        'city': 'Londrina',
        'state_uf': 'PR',
        'lat': -23.3045,
        'lon': -51.1696,
        'products': ['SOJA', 'MILHO', 'TRIGO'],
        'volumes': {'SOJA': '250000 ton/ano', 'MILHO': '150000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Fazenda Oeste do Paraná - Cascavel',
        'city': 'Cascavel',
        'state_uf': 'PR',
        'lat': -24.9557,
        'lon': -53.4552,
        'products': ['SOJA', 'MILHO', 'AVEIA'],
        'volumes': {'SOJA': '180000 ton/ano', 'MILHO': '100000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # SANTA CATARINA - Suínos/Aves
    {
        'name': 'Cooperativa Aurora',
        'city': 'Chapecó',
        'state_uf': 'SC',
        'lat': -27.1009,
        'lon': -52.6157,
        'products': ['SUÍNOS', 'AVES', 'MILHO'],
        'volumes': {'SUÍNOS': '200000 cabeças/ano', 'AVES': '500000 cabeças/ano'},
        'market_channel': 'Direto'
    },
    {
        'name': 'Fazenda Vale do Contestado - Canoinhas',
        'city': 'Canoinhas',
        'state_uf': 'SC',
        'lat': -26.1765,
        'lon': -50.3950,
        'products': ['CEBOLA', 'ALHO', 'BATATA'],
        'volumes': {'CEBOLA': '40000 ton/ano', 'ALHO': '15000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # RIO GRANDE DO SUL - Soja/Arroz
    {
        'name': 'Cooperativa Riograndense - Passo Fundo',
        'city': 'Passo Fundo',
        'state_uf': 'RS',
        'lat': -28.2577,
        'lon': -52.4096,
        'products': ['SOJA', 'TRIGO', 'MILHO'],
        'volumes': {'SOJA': '200000 ton/ano', 'TRIGO': '80000 ton/ano'},
        'market_channel': 'Exportação'
    },
    {
        'name': 'Arrozistas do Sul - Pelotas',
        'city': 'Pelotas',
        'state_uf': 'RS',
        'lat': -31.7719,
        'lon': -52.3420,
        'products': ['ARROZ', 'SOJA'],
        'volumes': {'ARROZ': '150000 ton/ano', 'SOJA': '100000 ton/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Fazenda Uva do Pampa - Bento Gonçalves',
        'city': 'Bento Gonçalves',
        'state_uf': 'RS',
        'lat': -29.1714,
        'lon': -51.5188,
        'products': ['UVA', 'VINHO', 'MAÇÃ'],
        'volumes': {'UVA': '80000 ton/ano', 'VINHO': '5000000 litros/ano'},
        'market_channel': 'Exportação'
    },
    
    # PECUÁRIA - Regiões diversas
    {
        'name': 'Fazenda Boi Gordo - Barretos',
        'city': 'Barretos',
        'state_uf': 'SP',
        'lat': -20.5574,
        'lon': -48.5678,
        'products': ['BOI GORDO', 'MILHO'],
        'volumes': {'BOI GORDO': '80000 cabeças/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Agropecuária Pantanal - Corumbá',
        'city': 'Corumbá',
        'state_uf': 'MS',
        'lat': -19.0078,
        'lon': -57.6530,
        'products': ['BOI GORDO', 'CAVALO'],
        'volumes': {'BOI GORDO': '50000 cabeças/ano'},
        'market_channel': 'CEASA'
    },
    
    # FRUTICULTURA - Regiões diversas
    {
        'name': 'Fazenda Maçã do Sul - São Joaquim',
        'city': 'São Joaquim',
        'state_uf': 'SC',
        'lat': -28.2938,
        'lon': -49.9317,
        'products': ['MAÇÃ', 'PERA', 'UVA'],
        'volumes': {'MAÇÃ': '60000 ton/ano', 'PERA': '20000 ton/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Cooperativa Pêssego - Canguçu',
        'city': 'Canguçu',
        'state_uf': 'RS',
        'lat': -31.3950,
        'lon': -52.6756,
        'products': ['PÊSSEGO', 'AMEIXA', 'UVA'],
        'volumes': {'PÊSSEGO': '25000 ton/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Fazenda Mamão - Linhares',
        'city': 'Linhares',
        'state_uf': 'ES',
        'lat': -19.3958,
        'lon': -40.0724,
        'products': ['MAMÃO', 'BANANA'],
        'volumes': {'MAMÃO': '80000 ton/ano', 'BANANA': '40000 ton/ano'},
        'market_channel': 'CEASA'
    },
    
    # AGRICULTURA FAMILIAR
    {
        'name': 'Associação de Pequenos Produtores - Zona da Mata',
        'city': 'Viçosa',
        'state_uf': 'MG',
        'lat': -20.7564,
        'lon': -42.8823,
        'products': ['CAFÉ', 'HORTALIÇAS', 'FRUTAS'],
        'volumes': {'CAFÉ': '5000 sacas/ano', 'HORTALIÇAS': '2000 ton/ano'},
        'market_channel': 'Mercado Local'
    },
    {
        'name': 'Cooperativa de Agricultura Familiar - Assis',
        'city': 'Assis',
        'state_uf': 'SP',
        'lat': -22.6617,
        'lon': -50.4183,
        'products': ['MILHO', 'FEIJÃO', 'HORTALIÇAS'],
        'volumes': {'MILHO': '15000 ton/ano', 'FEIJÃO': '5000 ton/ano'},
        'market_channel': 'CEASA'
    },
    {
        'name': 'Cooperativa de Produtores Orgânicos - Curitiba',
        'city': 'Curitiba',
        'state_uf': 'PR',
        'lat': -25.4284,
        'lon': -49.2733,
        'products': ['HORTALIÇAS ORGÂNICAS', 'FRUTAS ORGÂNICAS'],
        'volumes': {'HORTALIÇAS ORGÂNICAS': '5000 ton/ano'},
        'market_channel': 'Mercado Local'
    },
]

def seed_produtores_brasil():
    """Insere produtores de todas as regiões do Brasil no banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    inserted = 0
    updated = 0
    
    for prod in PRODUTORES_BRASIL:
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
    
    print(f"✓ Produtores Brasil inseridos: {inserted}")
    print(f"✓ Produtores Brasil atualizados: {updated}")
    print(f"✓ Total: {inserted + updated}")

if __name__ == '__main__':
    seed_produtores_brasil()
