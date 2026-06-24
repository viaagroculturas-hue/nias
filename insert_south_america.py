import sqlite3
import json

conn = sqlite3.connect('nia_flv.db')
cursor = conn.cursor()

# Municípios da América do Sul com coordenadas e principais produtos
south_america_municipalities = [
    # === ARGENTINA ===
    {'ibge_code': 'AR001', 'name': 'Rosario', 'state_uf': 'AR-SF', 'lat': -32.9468, 'lon': -60.6393, 
     'products': ['SOJA', 'TRIGO', 'MILHO'], 'ceasa_ref': 'ROSRIO-AR', 'is_producer': 1},
    {'ibge_code': 'AR002', 'name': 'Bahía Blanca', 'state_uf': 'AR-BA', 'lat': -38.7183, 'lon': -62.2664,
     'products': ['TRIGO', 'CERVEJARIA', 'GADO_BOVINO'], 'ceasa_ref': 'BHI-AR', 'is_producer': 1},
    {'ibge_code': 'AR003', 'name': 'Córdoba', 'state_uf': 'AR-CB', 'lat': -31.4201, 'lon': -64.1888,
     'products': ['SOJA', 'MILHO', 'AMENDOIM'], 'ceasa_ref': 'COR-AR', 'is_producer': 1},
    {'ibge_code': 'AR004', 'name': 'San Miguel de Tucumán', 'state_uf': 'AR-TM', 'lat': -26.8083, 'lon': -65.2176,
     'products': ['CANA_DE_ACUCAR', 'CITROS', 'MANGA'], 'ceasa_ref': 'TUC-AR', 'is_producer': 1},
    {'ibge_code': 'AR005', 'name': 'Mendoza', 'state_uf': 'AR-MZ', 'lat': -32.8895, 'lon': -68.8458,
     'products': ['UVA', 'VINHO', 'OLIVA'], 'ceasa_ref': 'MZA-AR', 'is_producer': 1},
    {'ibge_code': 'AR006', 'name': 'Pergamino', 'state_uf': 'AR-BA', 'lat': -33.8896, 'lon': -60.5736,
     'products': ['SOJA', 'TRIGO', 'MILHO'], 'ceasa_ref': 'PER-AR', 'is_producer': 1},
    
    # === CHILE ===
    {'ibge_code': 'CL001', 'name': 'Temuco', 'state_uf': 'CL-AR', 'lat': -38.7359, 'lon': -72.5904,
     'products': ['TRIGO', 'BATATA', 'AVENA'], 'ceasa_ref': 'TEM-CL', 'is_producer': 1},
    {'ibge_code': 'CL002', 'name': 'Osorno', 'state_uf': 'CL-LR', 'lat': -40.5745, 'lon': -73.1319,
     'products': ['LEITE', 'GADO_BOVINO', 'TRIGO'], 'ceasa_ref': 'OSR-CL', 'is_producer': 1},
    {'ibge_code': 'CL003', 'name': 'Curicó', 'state_uf': 'CL-ML', 'lat': -34.9828, 'lon': -71.2411,
     'products': ['UVA', 'MAÇA', 'PÊSSEGO'], 'ceasa_ref': 'CUR-CL', 'is_producer': 1},
    {'ibge_code': 'CL004', 'name': 'Chillán', 'state_uf': 'CL-NB', 'lat': -36.6067, 'lon': -72.1034,
     'products': ['TRIGO', 'CEBOLA', 'TOMATE'], 'ceasa_ref': 'CHI-CL', 'is_producer': 1},
    {'ibge_code': 'CL005', 'name': 'Talca', 'state_uf': 'CL-ML', 'lat': -35.4232, 'lon': -71.6485,
     'products': ['VINHO', 'UVA', 'FRUTAS'], 'ceasa_ref': 'TLC-CL', 'is_producer': 1},
    
    # === URUGUAI ===
    {'ibge_code': 'UY001', 'name': 'Paysandú', 'state_uf': 'UY-PA', 'lat': -32.3215, 'lon': -58.0756,
     'products': ['SOJA', 'TRIGO', 'GADO_BOVINO'], 'ceasa_ref': 'PAY-UY', 'is_producer': 1},
    {'ibge_code': 'UY002', 'name': 'Young', 'state_uf': 'UY-RN', 'lat': -32.6985, 'lon': -57.6265,
     'products': ['ARROZ', 'SOJA', 'LEITE'], 'ceasa_ref': 'YNG-UY', 'is_producer': 1},
    {'ibge_code': 'UY003', 'name': 'Mercedes', 'state_uf': 'UY-SO', 'lat': -33.2555, 'lon': -58.0309,
     'products': ['GADO_BOVINO', 'LEITE', 'SOJA'], 'ceasa_ref': 'MER-UY', 'is_producer': 1},
    {'ibge_code': 'UY004', 'name': 'Artigas', 'state_uf': 'UY-AR', 'lat': -30.4019, 'lon': -56.4676,
     'products': ['SOJA', 'ARROZ', 'ALGODAO'], 'ceasa_ref': 'ART-UY', 'is_producer': 1},
    
    # === PARAGUAI ===
    {'ibge_code': 'PY001', 'name': 'Encarnación', 'state_uf': 'PY-IT', 'lat': -27.3306, 'lon': -55.8667,
     'products': ['SOJA', 'MANDIOCA', 'ALGODAO'], 'ceasa_ref': 'ENC-PY', 'is_producer': 1},
    {'ibge_code': 'PY002', 'name': 'Caaguazú', 'state_uf': 'PY-CG', 'lat': -25.4712, 'lon': -56.0164,
     'products': ['SOJA', 'ALGODAO', 'MILHO'], 'ceasa_ref': 'CAG-PY', 'is_producer': 1},
    {'ibge_code': 'PY003', 'name': 'Villarrica', 'state_uf': 'PY-GU', 'lat': -25.7804, 'lon': -56.4488,
     'products': ['MANDIOCA', 'SOJA', 'TRIGO'], 'ceasa_ref': 'VLL-PY', 'is_producer': 1},
    {'ibge_code': 'PY004', 'name': 'Caazapá', 'state_uf': 'PY-CZ', 'lat': -26.1942, 'lon': -56.3712,
     'products': ['SOJA', 'MANDIOCA', 'ALGODAO'], 'ceasa_ref': 'CAZ-PY', 'is_producer': 1},
    
    # === BOLÍVIA ===
    {'ibge_code': 'BO001', 'name': 'Santa Cruz de la Sierra', 'state_uf': 'BO-SC', 'lat': -17.7833, 'lon': -63.1821,
     'products': ['SOJA', 'CANA_DE_ACUCAR', 'MILHO'], 'ceasa_ref': 'SRZ-BO', 'is_producer': 1},
    {'ibge_code': 'BO002', 'name': 'Tarija', 'state_uf': 'BO-TJ', 'lat': -21.5314, 'lon': -64.7313,
     'products': ['VINHO', 'UVA', 'HORTIFRUTI'], 'ceasa_ref': 'TJA-BO', 'is_producer': 1},
    {'ibge_code': 'BO003', 'name': 'Sucre', 'state_uf': 'BO-CH', 'lat': -19.0353, 'lon': -65.2592,
     'products': ['HORTIFRUTI', 'MILHO', 'BATATA'], 'ceasa_ref': 'SUC-BO', 'is_producer': 1},
    {'ibge_code': 'BO004', 'name': 'Trinidad', 'state_uf': 'BO-BN', 'lat': -14.8333, 'lon': -64.9000,
     'products': ['ARROZ', 'SOJA', 'GADO_BOVINO'], 'ceasa_ref': 'TRI-BO', 'is_producer': 1},
    
    # === COLÔMBIA ===
    {'ibge_code': 'CO001', 'name': 'Palmira', 'state_uf': 'CO-VAC', 'lat': 3.5833, 'lon': -76.3000,
     'products': ['CANA_DE_ACUCAR', 'CAFE', 'CITROS'], 'ceasa_ref': 'PAL-CO', 'is_producer': 1},
    {'ibge_code': 'CO002', 'name': 'Armenia', 'state_uf': 'CO-QUI', 'lat': 4.5333, 'lon': -75.6833,
     'products': ['CAFE', 'BANANA', 'PLATANO'], 'ceasa_ref': 'ARM-CO', 'is_producer': 1},
    {'ibge_code': 'CO003', 'name': 'Bucaramanga', 'state_uf': 'CO-SAN', 'lat': 7.1254, 'lon': -73.1198,
     'products': ['CACAU', 'CAFE', 'HORTIFRUTI'], 'ceasa_ref': 'BUC-CO', 'is_producer': 1},
    {'ibge_code': 'CO004', 'name': 'Tuluá', 'state_uf': 'CO-VAC', 'lat': 4.0833, 'lon': -76.2000,
     'products': ['CANA_DE_ACUCAR', 'MILHO', 'SOJA'], 'ceasa_ref': 'TUL-CO', 'is_producer': 1},
    
    # === PERU ===
    {'ibge_code': 'PE001', 'name': 'Ica', 'state_uf': 'PE-ICA', 'lat': -14.0755, 'lon': -75.7342,
     'products': ['UVA', 'ESPARGO', 'ALGODAO'], 'ceasa_ref': 'ICA-PE', 'is_producer': 1},
    {'ibge_code': 'PE002', 'name': 'Trujillo', 'state_uf': 'PE-LAL', 'lat': -8.1150, 'lon': -79.0300,
     'products': ['CANA_DE_ACUCAR', 'ARROZ', 'MILHO'], 'ceasa_ref': 'TRU-PE', 'is_producer': 1},
    {'ibge_code': 'PE003', 'name': 'Arequipa', 'state_uf': 'PE-ARE', 'lat': -16.4090, 'lon': -71.5375,
     'products': ['LEITE', 'GADO_BOVINO', 'ALFALFA'], 'ceasa_ref': 'ARQ-PE', 'is_producer': 1},
    {'ibge_code': 'PE004', 'name': 'Chiclayo', 'state_uf': 'PE-LAM', 'lat': -6.7700, 'lon': -79.8400,
     'products': ['ARROZ', 'CANA_DE_ACUCAR', 'ALGODAO'], 'ceasa_ref': 'CHI-PE', 'is_producer': 1},
    
    # === EQUADOR ===
    {'ibge_code': 'EC001', 'name': 'Guayaquil', 'state_uf': 'EC-GUA', 'lat': -2.1894, 'lon': -79.8891,
     'products': ['CACAU', 'BANANA', 'ARROZ'], 'ceasa_ref': 'GYE-EC', 'is_producer': 1},
    {'ibge_code': 'EC002', 'name': 'Quevedo', 'state_uf': 'EC-LOS', 'lat': -1.0333, 'lon': -79.4500,
     'products': ['CACAU', 'PALMA_ACEITERA', 'ARROZ'], 'ceasa_ref': 'QUE-EC', 'is_producer': 1},
    
    # === VENEZUELA ===
    {'ibge_code': 'VE001', 'name': 'Valencia', 'state_uf': 'VE-CAR', 'lat': 10.1667, 'lon': -68.0000,
     'products': ['LARANJA', 'CANA_DE_ACUCAR', 'MILHO'], 'ceasa_ref': 'VAL-VE', 'is_producer': 1},
    {'ibge_code': 'VE002', 'name': 'Maracaibo', 'state_uf': 'VE-ZUL', 'lat': 10.6500, 'lon': -71.6333,
     'products': ['ALGODAO', 'MILHO', 'ARROZ'], 'ceasa_ref': 'MAR-VE', 'is_producer': 1},
]

# Inserir municípios
inserted = 0
for mun in south_america_municipalities:
    # Verificar se já existe
    cursor.execute("SELECT id FROM flv_municipalities WHERE ibge_code = ?", (mun['ibge_code'],))
    if cursor.fetchone():
        print(f"⚠️  {mun['name']} já existe, pulando...")
        continue
    
    cursor.execute("""
        INSERT INTO flv_municipalities 
        (ibge_code, name, state_uf, lat, lon, is_producer, ceasa_ref, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (mun['ibge_code'], mun['name'], mun['state_uf'], mun['lat'], mun['lon'], 
          mun['is_producer'], mun['ceasa_ref']))
    inserted += 1
    print(f"✅ {mun['name']} ({mun['state_uf']}) - {', '.join(mun['products'])}")

conn.commit()
print(f"\n🌎 {inserted} municípios inseridos!")

# Verificar total
cursor.execute("SELECT COUNT(*) FROM flv_municipalities")
print(f"📊 Total de municípios no sistema: {cursor.fetchone()[0]}")

# Mostrar por país
print("\n📍 Distribuição por país:")
countries = {
    'AR': 'Argentina', 'CL': 'Chile', 'UY': 'Uruguai', 'PY': 'Paraguai',
    'BO': 'Bolívia', 'CO': 'Colômbia', 'PE': 'Peru', 'EC': 'Equador', 'VE': 'Venezuela'
}
for code, name in countries.items():
    cursor.execute("SELECT COUNT(*) FROM flv_municipalities WHERE ibge_code LIKE ?", (f'{code}%',))
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"  {name}: {count} municípios")

conn.close()
print("\n✅ Sistema atualizado com dados da América do Sul!")
