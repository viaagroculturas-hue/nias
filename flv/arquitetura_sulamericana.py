"""
Arquitetura de Inteligência Agrícola Sul-Americana
Clusters geográficos, sazonalidade e camadas de risco
"""

# ═══════════════════════════════════════════════════════════════
# 1. CLUSTERS GEOGRÁFICOS - Polígonos Produtivos
# ═══════════════════════════════════════════════════════════════

CLUSTERS_SULAMERICANOS = {
    # CLUSTER PAMPAS (Argentina/Uruguai)
    'pampas': {
        'nome': 'Cluster Pampas',
        'paises': ['AR', 'UY'],
        'centroid': [-33.0, -60.5],
        'polos': [
            {
                'id': 'AR-ROS-PAMPA',
                'nome': 'Gran Rosário',
                'cidade': 'Rosário',
                'estado': 'Santa Fe',
                'pais': 'AR',
                'lat': -32.95,
                'lon': -60.65,
                'culturas': ['SOJA', 'MILHO', 'TRIGO'],
                'area_ha': 850000,
                'safra_principal': 'Soja - Fev/Mar',
                'safra_segunda': 'Milho - Jun/Jul',
                'porto_ref': 'rosario',
                'corredor': 'Hidrovia Paraná-Paraguai'
            },
            {
                'id': 'AR-COR-PAMPA',
                'nome': 'Córdoba Central',
                'cidade': 'Córdoba',
                'estado': 'Córdoba',
                'pais': 'AR',
                'lat': -31.42,
                'lon': -64.18,
                'culturas': ['SOJA', 'MILHO', 'CEVADA'],
                'area_ha': 620000,
                'safra_principal': 'Soja - Mar/Abr',
                'safra_segunda': 'Milho - Jul/Ago',
                'porto_ref': 'rosario',
                'corredor': 'Ferrovia Belgrano'
            },
            {
                'id': 'AR-SFE-PAMPA',
                'nome': 'Santa Fe Norte',
                'cidade': 'Santa Fe',
                'estado': 'Santa Fe',
                'pais': 'AR',
                'lat': -31.61,
                'lon': -60.70,
                'culturas': ['SOJA', 'TRIGO', 'GIRASSOL'],
                'area_ha': 480000,
                'safra_principal': 'Soja - Mar/Abr',
                'safra_segunda': 'Trigo - Nov/Dez',
                'porto_ref': 'san_martin',
                'corredor': 'Hidrovia Paraná'
            },
            {
                'id': 'AR-QUE-PAMPA',
                'nome': 'Puerto Quequén',
                'cidade': 'Necochea',
                'estado': 'Buenos Aires',
                'pais': 'AR',
                'lat': -38.55,
                'lon': -58.75,
                'culturas': ['TRIGO', 'CEVADA', 'AVEIA'],
                'area_ha': 320000,
                'safra_principal': 'Trigo - Nov/Dez',
                'safra_segunda': 'Cevada - Out/Nov',
                'porto_ref': 'quequen',
                'corredor': 'Costa Atlântica'
            },
            {
                'id': 'UY-PAY-PAMPA',
                'nome': 'Paysandú',
                'cidade': 'Paysandú',
                'estado': 'Paysandú',
                'pais': 'UY',
                'lat': -32.32,
                'lon': -58.08,
                'culturas': ['SOJA', 'TRIGO', 'CEVADA'],
                'area_ha': 280000,
                'safra_principal': 'Soja - Fev/Mar',
                'safra_segunda': 'Trigo - Nov/Dez',
                'porto_ref': 'nueva_palmira',
                'corredor': 'Rio Uruguai'
            }
        ]
    },
    
    # CLUSTER CHACO (Paraguai/Bolívia)
    'chaco': {
        'nome': 'Cluster Chaco',
        'paises': ['PY', 'BO'],
        'centroid': [-20.0, -60.0],
        'polos': [
            {
                'id': 'PY-CDE-CHACO',
                'nome': 'Alto Paraná',
                'cidade': 'Ciudad del Este',
                'estado': 'Alto Paraná',
                'pais': 'PY',
                'lat': -25.51,
                'lon': -54.61,
                'culturas': ['SOJA', 'MILHO', 'TRIGO'],
                'area_ha': 450000,
                'safra_principal': 'Soja - Jan/Fev',
                'safra_segunda': 'Milho - Jun/Jul',
                'porto_ref': 'Puerto Caacupé',
                'corredor': 'Hidrovia Paraná'
            },
            {
                'id': 'PY-BOQ-CHACO',
                'nome': 'Chaco Seco',
                'cidade': 'Filadelfia',
                'estado': 'Boquerón',
                'pais': 'PY',
                'lat': -22.35,
                'lon': -60.05,
                'culturas': ['SOJA', 'ALGODÃO', 'SORGO'],
                'area_ha': 380000,
                'safra_principal': 'Soja - Fev/Mar',
                'safra_segunda': 'Algodão - Jul/Ago',
                'porto_ref': 'Puerto Villeta',
                'corredor': 'Rio Paraguai'
            },
            {
                'id': 'BO-SAN-CHACO',
                'nome': 'Santa Cruz de la Sierra',
                'cidade': 'Santa Cruz de la Sierra',
                'estado': 'Santa Cruz',
                'pais': 'BO',
                'lat': -17.78,
                'lon': -63.18,
                'culturas': ['SOJA', 'MILHO', 'GIRASSOL'],
                'area_ha': 520000,
                'safra_principal': 'Soja - Abr/Mai',
                'safra_segunda': 'Milho - Ago/Set',
                'porto_ref': 'Puerto Gravetal',
                'corredor': 'Ferrovia Oriental'
            },
            {
                'id': 'BO-TRI-CHACO',
                'nome': 'Trinidad',
                'cidade': 'Trinidad',
                'estado': 'Beni',
                'pais': 'BO',
                'lat': -14.83,
                'lon': -64.90,
                'culturas': ['ARROZ', 'SOJA'],
                'area_ha': 180000,
                'safra_principal': 'Arroz - Jun/Jul',
                'safra_segunda': 'Soja - Fev/Mar',
                'porto_ref': 'Puerto Guayaramerín',
                'corredor': 'Rio Mamoré'
            }
        ]
    },
    
    # CLUSTER ANDINO (Chile/Peru/Equador)
    'andino': {
        'nome': 'Cluster Andino',
        'paises': ['CL', 'PE', 'EC'],
        'centroid': [-15.0, -70.0],
        'polos': [
            {
                'id': 'CL-VAL-ANDINO',
                'nome': 'Vale Central',
                'cidade': 'Rancagua',
                'estado': "O'Higgins",
                'pais': 'CL',
                'lat': -34.17,
                'lon': -70.74,
                'culturas': ['UVA', 'MAÇÃ', 'PÊSSEGO', 'CEREJA'],
                'area_ha': 120000,
                'safra_principal': 'Uva - Fev/Abr',
                'safra_segunda': 'Maçã - Mar/Mai',
                'porto_ref': 'Puerto San Antonio',
                'corredor': 'Ruta 5 Panamericana'
            },
            {
                'id': 'CL-CUR-ANDINO',
                'nome': 'Curicó',
                'cidade': 'Curicó',
                'estado': 'Maule',
                'pais': 'CL',
                'lat': -34.98,
                'lon': -71.24,
                'culturas': ['UVA', 'ABACATE', 'CEREJA'],
                'area_ha': 95000,
                'safra_principal': 'Uva - Nov/Jan',
                'safra_segunda': 'Cereja - Nov/Dez',
                'porto_ref': 'Puerto San Antonio',
                'corredor': 'Ruta 5 Panamericana'
            },
            {
                'id': 'PE-ICA-ANDINO',
                'nome': 'Vale de Ica',
                'cidade': 'Ica',
                'estado': 'Ica',
                'pais': 'PE',
                'lat': -14.07,
                'lon': -75.73,
                'culturas': ['ASPARGOS', 'UVA', 'PALTA'],
                'area_ha': 65000,
                'safra_principal': 'Aspargos - Set/Out',
                'safra_segunda': 'Uva - Nov/Jan',
                'porto_ref': 'pisco',
                'corredor': 'Panamericana Sur'
            },
            {
                'id': 'PE-LIM-ANDINO',
                'nome': 'Lima Norte',
                'cidade': 'Chancay',
                'estado': 'Lima',
                'pais': 'PE',
                'lat': -11.56,
                'lon': -77.27,
                'culturas': ['UVA', 'MANGA', 'LIMÃO'],
                'area_ha': 45000,
                'safra_principal': 'Uva - Out/Dez',
                'safra_segunda': 'Manga - Jan/Mar',
                'porto_ref': 'callao',
                'corredor': 'Panamericana Norte'
            },
            {
                'id': 'EC-GUA-ANDINO',
                'nome': 'Guayaquil',
                'cidade': 'Guayaquil',
                'estado': 'Guayas',
                'pais': 'EC',
                'lat': -2.19,
                'lon': -79.88,
                'culturas': ['BANANA', 'CACAU', 'PALMA'],
                'area_ha': 180000,
                'safra_principal': 'Banana - Todo ano',
                'safra_segunda': 'Cacau - Mai/Jun',
                'porto_ref': 'guayaquil',
                'corredor': 'Costa Pacífica'
            }
        ]
    },
    
    # CLUSTER TROPICAL (Colômbia) - Potência do Arábica e Flores
    'tropical': {
        'nome': 'Cluster Tropical',
        'paises': ['CO'],
        'centroid': [4.5, -74.0],
        'polos': [
            {
                'id': 'CO-EJE-CAFE',
                'nome': 'Eixo Cafeeiro - Quindío',
                'cidade': 'Armenia',
                'estado': 'Quindío',
                'pais': 'CO',
                'lat': 4.53,
                'lon': -75.70,
                'culturas': ['CAFE', 'BANANA'],
                'area_ha': 380000,
                'safra_principal': 'Café - Out/Dez',
                'safra_segunda': 'Banana - Todo ano',
                'porto_ref': 'buenaventura',
                'corredor': 'Ferrovia del Café'
            },
            {
                'id': 'CO-SAV-FLORES',
                'nome': 'Savana de Bogotá - Flores',
                'cidade': 'Cajicá',
                'estado': 'Cundinamarca',
                'pais': 'CO',
                'lat': 4.92,
                'lon': -74.02,
                'culturas': ['FLORES', 'ROSAS'],
                'area_ha': 8500,
                'safra_principal': 'Flores - Todo ano',
                'safra_segunda': '',
                'porto_ref': 'bogota',
                'corredor': 'Aéreo/Eldorado'
            },
            {
                'id': 'CO-ANT-ABACATE',
                'nome': 'Antioquia - Abacate',
                'cidade': 'Medellín',
                'estado': 'Antioquia',
                'pais': 'CO',
                'lat': 6.25,
                'lon': -75.56,
                'culturas': ['ABACATE', 'BANANA'],
                'area_ha': 45000,
                'safra_principal': 'Abacate - Todo ano',
                'safra_segunda': 'Banana - Todo ano',
                'porto_ref': 'cartagena',
                'corredor': 'Carretera al Mar'
            },
            {
                'id': 'CO-MAG-BANANA',
                'nome': 'Magdalena - Bananas',
                'cidade': 'Santa Marta',
                'estado': 'Magdalena',
                'pais': 'CO',
                'lat': 11.24,
                'lon': -74.21,
                'culturas': ['BANANA', 'CACAU'],
                'area_ha': 95000,
                'safra_principal': 'Banana - Todo ano',
                'safra_segunda': 'Cacau - Mai/Jul',
                'porto_ref': 'santa_marta',
                'corredor': 'Costa Caribe'
            },
            {
                'id': 'CO-MET-PALMA',
                'nome': 'Meta - Palma de Óleo',
                'cidade': 'Villavicencio',
                'estado': 'Meta',
                'pais': 'CO',
                'lat': 4.12,
                'lon': -73.62,
                'culturas': ['PALMA', 'CACAU'],
                'area_ha': 180000,
                'safra_principal': 'Palma - Todo ano',
                'safra_segunda': 'Cacau - Mai/Jul',
                'porto_ref': 'barrancabermeja',
                'corredor': 'Rio Meta'
            },
            {
                'id': 'CO-BOG-HORT',
                'nome': 'Altiplano Cundiboyacense',
                'cidade': 'Tunja',
                'estado': 'Boyacá',
                'pais': 'CO',
                'lat': 5.54,
                'lon': -73.36,
                'culturas': ['BATATA', 'CEBOLA', 'HORTALICAS'],
                'area_ha': 85000,
                'safra_principal': 'Batata - Mar/Mai',
                'safra_segunda': 'Cebola - Ago/Out',
                'porto_ref': 'bogota',
                'corredor': 'Carretera Central'
            }
        ]
    },
    
    # CLUSTER VENEZUELA - Retomada dos Grãos
    'venezuela': {
        'nome': 'Cluster Venezuela',
        'paises': ['VE'],
        'centroid': [7.0, -66.0],
        'polos': [
            {
                'id': 'VE-POR-MILHO',
                'nome': 'Portuguesa - Celeiro do Milho',
                'cidade': 'Guanare',
                'estado': 'Portuguesa',
                'pais': 'VE',
                'lat': 9.04,
                'lon': -69.74,
                'culturas': ['MILHO', 'SORGO'],
                'area_ha': 280000,
                'safra_principal': 'Milho - Nov/Dez',
                'safra_segunda': 'Sorgo - Jan/Fev',
                'porto_ref': 'la_guaira',
                'corredor': 'Carretera Central'
            },
            {
                'id': 'VE-GUA-ARROZ',
                'nome': 'Guárico - Arroz Irrigado',
                'cidade': 'Calabozo',
                'estado': 'Guárico',
                'pais': 'VE',
                'lat': 8.92,
                'lon': -67.42,
                'culturas': ['ARROZ', 'MILHO'],
                'area_ha': 120000,
                'safra_principal': 'Arroz - Jul/Ago',
                'safra_segunda': 'Milho - Nov/Dez',
                'porto_ref': 'la_guaira',
                'corredor': 'Rio Guárico'
            },
            {
                'id': 'VE-LAR-CANA',
                'nome': 'Lara - Cana-de-Açúcar',
                'cidade': 'Carora',
                'estado': 'Lara',
                'pais': 'VE',
                'lat': 10.18,
                'lon': -70.08,
                'culturas': ['CANA', 'SORGO'],
                'area_ha': 85000,
                'safra_principal': 'Cana - Mai/Out',
                'safra_segunda': 'Sorgo - Nov/Jan',
                'porto_ref': 'puerto_cabello',
                'corredor': 'Carretera Lara-Zulia'
            },
            {
                'id': 'VE-ZUL-SORGO',
                'nome': 'Zulia - Sorgo e Grãos',
                'cidade': 'Maracaibo',
                'estado': 'Zulia',
                'pais': 'VE',
                'lat': 10.65,
                'lon': -71.63,
                'culturas': ['SORGO', 'MILHO', 'GERGELIM'],
                'area_ha': 150000,
                'safra_principal': 'Sorgo - Dez/Fev',
                'safra_segunda': 'Milho - Abr/Jun',
                'porto_ref': 'maracaibo',
                'corredor': 'Lago de Maracaibo'
            }
        ]
    }
}

# ═══════════════════════════════════════════════════════════════
# 2. MATRIZ DE PRODUTOS POR SAZONALIDADE
# ═══════════════════════════════════════════════════════════════

MATRIZ_SAZONALIDADE = {
    # GRÃOS
    'soja': {
        'nome': 'Soja',
        'ciclo_dias': 120,
        'sazonalidade': {
            'BR-MT': {'plantio': 'Set-Out', 'colheita': 'Fev-Mar', 'pico_export': 'Mar-Mai'},
            'BR-PR': {'plantio': 'Out-Nov', 'colheita': 'Fev-Abr', 'pico_export': 'Mar-Mai'},
            'BR-RS': {'plantio': 'Out-Nov', 'colheita': 'Mar-Abr', 'pico_export': 'Abr-Jun'},
            'AR-PAMPA': {'plantio': 'Out-Nov', 'colheita': 'Abr-Mai', 'pico_export': 'Mai-Jul'},
            'PY-CHACO': {'plantio': 'Set-Out', 'colheita': 'Jan-Fev', 'pico_export': 'Fev-Abr'},
            'BO-CHACO': {'plantio': 'Out-Nov', 'colheita': 'Abr-Mai', 'pico_export': 'Mai-Jul'}
        },
        'corredores_log': ['Hidrovia Paraná-Paraguai', 'Ferrovia Norte-Sul', 'Corredor Bioceânico'],
        'portos_saida': ['santos', 'paranagua', 'rosario', 'san_antonio'],
        'risco_clima': ['Estiagem Jan-Fev', 'Geada Jul-Ago'],
        'arbitragem_ceasa': False
    },
    
    'milho': {
        'nome': 'Milho',
        'ciclo_dias': 140,
        'sazonalidade': {
            'BR-MT': {'plantio': 'Fev-Mar', 'colheita': 'Jun-Jul', 'pico_export': 'Jul-Set'},
            'BR-PR': {'plantio': 'Ago-Set', 'colheita': 'Jan-Fev', 'pico_export': 'Fev-Abr'},
            'BR-RS': {'plantio': 'Set-Out', 'colheita': 'Fev-Mar', 'pico_export': 'Mar-Mai'},
            'AR-PAMPA': {'plantio': 'Out-Nov', 'colheita': 'Mar-Abr', 'pico_export': 'Abr-Jun'},
            'PY-CHACO': {'plantio': 'Ago-Set', 'colheita': 'Jan-Fev', 'pico_export': 'Fev-Mar'}
        },
        'corredores_log': ['Hidrovia Paraná-Paraguai', 'Ferrovia Oeste-Leste'],
        'portos_saida': ['santos', 'paranagua', 'rosario'],
        'risco_clima': ['Estiagem Dez-Jan'],
        'arbitragem_ceasa': False
    },
    
    'trigo': {
        'nome': 'Trigo',
        'ciclo_dias': 160,
        'sazonalidade': {
            'AR-PAMPA': {'plantio': 'Jun-Jul', 'colheita': 'Nov-Dez', 'pico_export': 'Dez-Fev'},
            'BR-RS': {'plantio': 'Mai-Jun', 'colheita': 'Out-Nov', 'pico_export': 'Nov-Jan'},
            'BR-PR': {'plantio': 'Abr-Mai', 'colheita': 'Set-Out', 'pico_export': 'Out-Dez'},
            'PY-CHACO': {'plantio': 'Mai-Jun', 'colheita': 'Out-Nov', 'pico_export': 'Nov-Jan'}
        },
        'corredores_log': ['Ferrovia Belgrano', 'Hidrovia Paraná'],
        'portos_saida': ['quequen', 'rosario', 'san_antonio'],
        'risco_clima': ['Geadas Ago-Set', 'Chuvas excessivas Out'],
        'arbitragem_ceasa': False
    },
    
    # HORTIFRUTI
    'batata': {
        'nome': 'Batata',
        'ciclo_dias': 90,
        'sazonalidade': {
            'AR-VALLE': {'plantio': 'Ago-Set', 'colheita': 'Nov-Jan', 'pico_export': 'Dez-Fev'},
            'BR-MG': {'plantio': 'Fev-Mar', 'colheita': 'Mai-Jun', 'pico_export': 'Jun-Ago'},
            'BR-RS': {'plantio': 'Ago-Set', 'colheita': 'Nov-Dez', 'pico_export': 'Dez-Fev'}
        },
        'corredores_log': ['Ruta 14', 'BR-116'],
        'portos_saida': ['santos', 'san_antonio'],
        'risco_clima': ['Geadas', 'Excesso de chuva'],
        'arbitragem_ceasa': True,
        'ceasa_ref': 'CEAGESP'
    },
    
    'cebola': {
        'nome': 'Cebola',
        'ciclo_dias': 120,
        'sazonalidade': {
            'AR-RIONEGRO': {'plantio': 'Set-Out', 'colheita': 'Fev-Mar', 'pico_export': 'Mar-Mai'},
            'BR-GO': {'plantio': 'Mar-Abr', 'colheita': 'Jul-Ago', 'pico_export': 'Ago-Out'},
            'BR-RS': {'plantio': 'Ago-Set', 'colheita': 'Dez-Jan', 'pico_export': 'Jan-Mar'}
        },
        'corredores_log': ['BR-153', 'Ruta 14'],
        'portos_saida': ['santos', 'san_antonio'],
        'risco_clima': ['Estiagem', 'Doenças por umidade'],
        'arbitragem_ceasa': True,
        'ceasa_ref': 'CEAGESP'
    },
    
    'tomate_industria': {
        'nome': 'Tomate Indústria',
        'ciclo_dias': 110,
        'sazonalidade': {
            'BR-GO': {'plantio': 'Ago-Set', 'colheita': 'Nov-Jan', 'pico_export': 'Dez-Fev'},
            'BR-MG': {'plantio': 'Set-Out', 'colheita': 'Dez-Fev', 'pico_export': 'Jan-Mar'},
            'BR-SP': {'plantio': 'Ago-Set', 'colheita': 'Nov-Jan', 'pico_export': 'Dez-Fev'}
        },
        'corredores_log': ['BR-050', 'BR-153'],
        'portos_saida': ['santos'],
        'risco_clima': ['Chuvas excessivas', 'Estiagem prolongada'],
        'arbitragem_ceasa': True,
        'ceasa_ref': 'CEAGESP'
    },
    
    # FRUTAS
    'uva': {
        'nome': 'Uva',
        'ciclo_dias': 365,
        'sazonalidade': {
            'CL-VALE': {'plantio': 'Todo ano', 'colheita': 'Nov-Abr', 'pico_export': 'Dez-Mar'},
            'BR-SP': {'plantio': 'Todo ano', 'colheita': 'Jan-Mar', 'pico_export': 'Fev-Abr'},
            'PE-ICA': {'plantio': 'Todo ano', 'colheita': 'Set-Jan', 'pico_export': 'Out-Jan'},
            'AR-MENDOZA': {'plantio': 'Todo ano', 'colheita': 'Fev-Abr', 'pico_export': 'Mar-Mai'}
        },
        'corredores_log': ['Ruta 5', 'BR-116'],
        'portos_saida': ['san_antonio', 'santos', 'callao'],
        'risco_clima': ['Geadas', 'Granizo'],
        'arbitragem_ceasa': True,
        'ceasa_ref': 'CEAGESP'
    },
    
    'banana': {
        'nome': 'Banana',
        'ciclo_dias': 365,
        'sazonalidade': {
            'EC-GUAYAQUIL': {'plantio': 'Todo ano', 'colheita': 'Todo ano', 'pico_export': 'Mai-Ago'},
            'BR-BA': {'plantio': 'Todo ano', 'colheita': 'Todo ano', 'pico_export': 'Todo ano'},
            'CO-MAG': {'plantio': 'Todo ano', 'colheita': 'Todo ano', 'pico_export': 'Todo ano'}
        },
        'corredores_log': ['Costa Pacífica', 'BR-101'],
        'portos_saida': ['guayaquil', 'santos', 'buenaventura'],
        'risco_clima': ['Ventos fortes', 'Excesso de chuva'],
        'arbitragem_ceasa': True,
        'ceasa_ref': 'CEAGESP'
    },
    
    # CAFÉ
    'cafe': {
        'nome': 'Café',
        'ciclo_dias': 365,
        'sazonalidade': {
            'BR-MG': {'plantio': 'Out-Nov', 'colheita': 'Mai-Set', 'pico_export': 'Jun-Out'},
            'BR-SP': {'plantio': 'Out-Nov', 'colheita': 'Mai-Ago', 'pico_export': 'Jun-Set'},
            'CO-EJE': {'plantio': 'Mar-Abr', 'colheita': 'Out-Dez', 'pico_export': 'Nov-Jan'},
            'PE-CAJA': {'plantio': 'Fev-Mar', 'colheita': 'Jun-Ago', 'pico_export': 'Jul-Set'}
        },
        'corredores_log': ['Ferrovia del Café', 'BR-381'],
        'portos_saida': ['santos', 'buenaventura', 'callao'],
        'risco_clima': ['Geada Jun-Ago', 'Estiagem prolongada'],
        'arbitragem_ceasa': False
    }
}

# ═══════════════════════════════════════════════════════════════
# 3. CAMADAS DE RISCO (OVERLAY)
# ═══════════════════════════════════════════════════════════════

CAMADAS_RISCO = {
    'ndvi_sentinel': {
        'nome': 'NDVI Sentinel-2',
        'fonte': 'Copernicus',
        'resolucao': '10m',
        'frequencia': '5 dias',
        'url_api': 'https://services.sentinel-hub.com/api/v1/process',
        'indicadores': [
            {'range': [0.0, 0.2], 'classe': 'Água/Solo exposto', 'cor': '#a50026', 'alerta': False},
            {'range': [0.2, 0.4], 'classe': 'Vegetação esparsa/Estresse', 'cor': '#f46d43', 'alerta': False},
            {'range': [0.4, 0.6], 'classe': 'Vegetação moderada', 'cor': '#fee08b', 'alerta': False},
            {'range': [0.6, 0.8], 'classe': 'Vegetação saudável', 'cor': '#d9ef8b', 'alerta': False},
            {'range': [0.8, 1.0], 'classe': 'Vegetação densa', 'cor': '#1a9850', 'alerta': False}
        ]
    },
    
    'evi_modis': {
        'nome': 'EVI MODIS',
        'fonte': 'NASA',
        'resolucao': '250m',
        'frequencia': '16 dias',
        'url_api': 'https://modis.gsfc.nasa.gov/data/dataprod/mod13.php',
        'indicadores': [
            {'range': [0.0, 0.2], 'classe': 'Baixa produtividade', 'cor': '#d73027', 'alerta': False},
            {'range': [0.2, 0.5], 'classe': 'Produtividade moderada', 'cor': '#fc8d59', 'alerta': False},
            {'range': [0.5, 0.8], 'classe': 'Alta produtividade', 'cor': '#91cf60', 'alerta': False},
            {'range': [0.8, 1.0], 'classe': 'Produtividade máxima', 'cor': '#1a9850', 'alerta': False}
        ]
    },
    
    'smap_soil_moisture': {
        'nome': 'Umidade do Solo SMAP',
        'fonte': 'NASA',
        'resolucao': '9km',
        'frequencia': '3 dias',
        'url_api': 'https://nsidc.org/data/smap/smap-data.html',
        'indicadores': [
            {'range': [0.0, 0.15], 'classe': 'Seca severa', 'cor': '#8B0000', 'alerta': True},
            {'range': [0.15, 0.30], 'classe': 'Seca moderada', 'cor': '#FF4500', 'alerta': True},
            {'range': [0.30, 0.50], 'classe': 'Umidade adequada', 'cor': '#FFD700', 'alerta': False},
            {'range': [0.50, 0.70], 'classe': 'Umidade ótima', 'cor': '#32CD32', 'alerta': False},
            {'range': [0.70, 1.0], 'classe': 'Saturação/Alagamento', 'cor': '#00008B', 'alerta': True}
        ]
    },
    
    'chirps_precip': {
        'nome': 'Precipitação CHIRPS',
        'fonte': 'USGS',
        'resolucao': '5km',
        'frequencia': 'Diária',
        'url_api': 'https://data.chc.ucsb.edu/products/CHIRPS-2.0/',
        'indicadores': [
            {'range': [0, 10], 'classe': 'Seca', 'cor': '#8B4513', 'alerta': False},
            {'range': [10, 50], 'classe': 'Chuva leve', 'cor': '#87CEEB', 'alerta': False},
            {'range': [50, 100], 'classe': 'Chuva moderada', 'cor': '#4169E1', 'alerta': False},
            {'range': [100, 200], 'classe': 'Chuva forte', 'cor': '#0000CD', 'alerta': False},
            {'range': [200, 500], 'classe': 'Chuva extrema', 'cor': '#8B0000', 'alerta': True}
        ]
    }
}

# ═══════════════════════════════════════════════════════════════
# 4. PORTOS E CORREDORES LOGÍSTICOS
# ═══════════════════════════════════════════════════════════════

PORTOS_ESTRATEGICOS = {
    'santos': {
        'nome': 'Porto de Santos',
        'pais': 'BR',
        'lat': -23.9608,
        'lon': -46.3331,
        'capacidade_graos_ton_dia': 150000,
        'capacidade_containers_teu_dia': 5000,
        'tempo_espera_medio_horas': 48,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    'paranagua': {
        'nome': 'Porto de Paranaguá',
        'pais': 'BR',
        'lat': -25.5026,
        'lon': -48.5090,
        'capacidade_graos_ton_dia': 120000,
        'capacidade_containers_teu_dia': 3000,
        'tempo_espera_medio_horas': 36,
        'status': 'Operacional',
        'risco': 'Baixo'
    },
    
    'rosario': {
        'nome': 'Puerto Rosario',
        'pais': 'AR',
        'lat': -32.9468,
        'lon': -60.6393,
        'capacidade_graos_ton_dia': 80000,
        'capacidade_containers_teu_dia': 1500,
        'tempo_espera_medio_horas': 72,
        'status': 'Operacional',
        'risco': 'Alto'
    },
    
    'san_antonio': {
        'nome': 'Puerto San Antonio',
        'pais': 'CL',
        'lat': -33.5800,
        'lon': -71.6200,
        'capacidade_graos_ton_dia': 60000,
        'capacidade_containers_teu_dia': 4000,
        'tempo_espera_medio_horas': 24,
        'status': 'Operacional',
        'risco': 'Baixo'
    },
    
    'callao': {
        'nome': 'Puerto del Callao',
        'pais': 'PE',
        'lat': -12.0500,
        'lon': -77.1333,
        'capacidade_graos_ton_dia': 40000,
        'capacidade_containers_teu_dia': 3500,
        'tempo_espera_medio_horas': 30,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    'guayaquil': {
        'nome': 'Puerto de Guayaquil',
        'pais': 'EC',
        'lat': -2.2038,
        'lon': -79.8797,
        'capacidade_graos_ton_dia': 50000,
        'capacidade_containers_teu_dia': 2800,
        'tempo_espera_medio_horas': 42,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    'buenaventura': {
        'nome': 'Puerto de Buenaventura',
        'pais': 'CO',
        'lat': 3.8800,
        'lon': -77.0300,
        'capacidade_graos_ton_dia': 45000,
        'capacidade_containers_teu_dia': 3200,
        'tempo_espera_medio_horas': 36,
        'status': 'Operacional',
        'risco': 'Alto'
    },
    
    # Portos adicionais mencionados nos clusters
    'quequen': {
        'nome': 'Puerto Quequén',
        'pais': 'AR',
        'lat': -38.5500,
        'lon': -58.7000,
        'capacidade_graos_ton_dia': 60000,
        'capacidade_containers_teu_dia': 800,
        'tempo_espera_medio_horas': 54,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    'san_martin': {
        'nome': 'Puerto San Martín',
        'pais': 'AR',
        'lat': -32.7167,
        'lon': -60.7333,
        'capacidade_graos_ton_dia': 70000,
        'capacidade_containers_teu_dia': 1200,
        'tempo_espera_medio_horas': 60,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    'nueva_palmira': {
        'nome': 'Puerto de Nueva Palmira',
        'pais': 'UY',
        'lat': -33.8833,
        'lon': -58.4167,
        'capacidade_graos_ton_dia': 50000,
        'capacidade_containers_teu_dia': 1000,
        'tempo_espera_medio_horas': 30,
        'status': 'Operacional',
        'risco': 'Baixo'
    },
    
    'bogota': {
        'nome': 'Puerto Seco de Bogotá',
        'pais': 'CO',
        'lat': 4.7110,
        'lon': -74.0721,
        'capacidade_graos_ton_dia': 25000,
        'capacidade_containers_teu_dia': 1500,
        'tempo_espera_medio_horas': 12,
        'status': 'Operacional',
        'risco': 'Baixo',
        'tipo': 'Porto Seco'
    },
    
    'barrancabermeja': {
        'nome': 'Puerto de Barrancabermeja',
        'pais': 'CO',
        'lat': 7.0667,
        'lon': -73.8500,
        'capacidade_graos_ton_dia': 30000,
        'capacidade_containers_teu_dia': 500,
        'tempo_espera_medio_horas': 24,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    'pisco': {
        'nome': 'Puerto de Pisco',
        'pais': 'PE',
        'lat': -13.7100,
        'lon': -76.2000,
        'capacidade_graos_ton_dia': 25000,
        'capacidade_containers_teu_dia': 2000,
        'tempo_espera_medio_horas': 18,
        'status': 'Operacional',
        'risco': 'Baixo'
    },
    
    'caacupe': {
        'nome': 'Puerto de Caacupé',
        'pais': 'PY',
        'lat': -25.3867,
        'lon': -57.1400,
        'capacidade_graos_ton_dia': 35000,
        'capacidade_containers_teu_dia': 600,
        'tempo_espera_medio_horas': 36,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    'villeta': {
        'nome': 'Puerto de Villeta',
        'pais': 'PY',
        'lat': -25.5000,
        'lon': -57.5000,
        'capacidade_graos_ton_dia': 40000,
        'capacidade_containers_teu_dia': 800,
        'tempo_espera_medio_horas': 42,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    'gravetal': {
        'nome': 'Puerto Gravetal',
        'pais': 'BO',
        'lat': -17.7500,
        'lon': -63.2000,
        'capacidade_graos_ton_dia': 30000,
        'capacidade_containers_teu_dia': 400,
        'tempo_espera_medio_horas': 48,
        'status': 'Operacional',
        'risco': 'Alto'
    },
    
    'guayaramerin': {
        'nome': 'Puerto de Guayaramerín',
        'pais': 'BO',
        'lat': -11.7333,
        'lon': -65.3500,
        'capacidade_graos_ton_dia': 20000,
        'capacidade_containers_teu_dia': 300,
        'tempo_espera_medio_horas': 36,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    # PORTOS DA COLÔMBIA (Caribe)
    'cartagena': {
        'nome': 'Puerto de Cartagena',
        'pais': 'CO',
        'lat': 10.4000,
        'lon': -75.5167,
        'capacidade_graos_ton_dia': 55000,
        'capacidade_containers_teu_dia': 4500,
        'tempo_espera_medio_horas': 24,
        'status': 'Operacional',
        'risco': 'Baixo'
    },
    
    'santa_marta': {
        'nome': 'Puerto de Santa Marta',
        'pais': 'CO',
        'lat': 11.2419,
        'lon': -74.2053,
        'capacidade_graos_ton_dia': 40000,
        'capacidade_containers_teu_dia': 2500,
        'tempo_espera_medio_horas': 30,
        'status': 'Operacional',
        'risco': 'Médio'
    },
    
    # PORTOS DA VENEZUELA (Caribe)
    'la_guaira': {
        'nome': 'Puerto de La Guaira',
        'pais': 'VE',
        'lat': 10.6000,
        'lon': -66.9333,
        'capacidade_graos_ton_dia': 35000,
        'capacidade_containers_teu_dia': 2800,
        'tempo_espera_medio_horas': 48,
        'status': 'Operacional',
        'risco': 'Alto'
    },
    
    'puerto_cabello': {
        'nome': 'Puerto de Puerto Cabello',
        'pais': 'VE',
        'lat': 10.4667,
        'lon': -68.0167,
        'capacidade_graos_ton_dia': 45000,
        'capacidade_containers_teu_dia': 3200,
        'tempo_espera_medio_horas': 42,
        'status': 'Operacional',
        'risco': 'Alto'
    },
    
    'maracaibo': {
        'nome': 'Puerto de Maracaibo',
        'pais': 'VE',
        'lat': 10.6500,
        'lon': -71.6333,
        'capacidade_graos_ton_dia': 30000,
        'capacidade_containers_teu_dia': 2000,
        'tempo_espera_medio_horas': 54,
        'status': 'Operacional',
        'risco': 'Alto'
    }
}

# Exportar para uso em outros módulos
if __name__ == '__main__':
    print("Arquitetura de Inteligência Agrícola Sul-Americana carregada")
    print(f"Clusters: {len(CLUSTERS_SULAMERICANOS)}")
    print(f"Produtos na matriz: {len(MATRIZ_SAZONALIDADE)}")
    print(f"Camadas de risco: {len(CAMADAS_RISCO)}")
    print(f"Portos estratégicos: {len(PORTOS_ESTRATEGICOS)}")
