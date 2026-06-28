"""
NIAS v2 — Base de dados geográfica real
Polos produtivos da América do Sul com coordenadas verificadas
Fonte: IBGE, CONAB, FAO, INDEC/Argentina, DANE/Colômbia, INE/Bolívia
"""

POLOS_SA = [

    # =========================================================
    # BRASIL — Centro-Oeste (maior polo de grãos do mundo)
    # =========================================================
    {
        "id": "br_sorriso",
        "nome": "Sorriso",
        "estado": "Mato Grosso", "pais": "Brasil", "iso": "BR",
        "lat": -12.5490, "lon": -55.7209,
        "culturas": ["soja", "milho", "algodão"],
        "especialidade": "grãos",
        "area_mha": 1.8,
        "volume_ref_mt": 6.2,
        "descricao": "Maior município produtor de soja do mundo",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_lucas_rio_verde",
        "nome": "Lucas do Rio Verde",
        "estado": "Mato Grosso", "pais": "Brasil", "iso": "BR",
        "lat": -13.0567, "lon": -55.9198,
        "culturas": ["soja", "milho", "algodão"],
        "especialidade": "grãos",
        "area_mha": 1.4,
        "volume_ref_mt": 5.1,
        "descricao": "Alto tecnologia — referência em produtividade de soja",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_nova_mutum",
        "nome": "Nova Mutum",
        "estado": "Mato Grosso", "pais": "Brasil", "iso": "BR",
        "lat": -13.8306, "lon": -56.0819,
        "culturas": ["soja", "milho"],
        "especialidade": "grãos",
        "area_mha": 1.1,
        "volume_ref_mt": 4.0,
        "descricao": "Polo de grãos com rápida expansão de área",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_campo_novo_parecis",
        "nome": "Campo Novo do Parecis",
        "estado": "Mato Grosso", "pais": "Brasil", "iso": "BR",
        "lat": -13.6725, "lon": -57.8946,
        "culturas": ["soja", "algodão", "girassol"],
        "especialidade": "grãos",
        "area_mha": 1.0,
        "volume_ref_mt": 3.5,
        "descricao": "Maior produtor de algodão de MT",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_rondonopolis",
        "nome": "Rondonópolis",
        "estado": "Mato Grosso", "pais": "Brasil", "iso": "BR",
        "lat": -16.4702, "lon": -54.6362,
        "culturas": ["soja", "milho", "pecuária"],
        "especialidade": "grãos+logística",
        "area_mha": 0.9,
        "volume_ref_mt": 3.1,
        "descricao": "Hub logístico — entroncamento MT-GO-MS",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_rio_verde",
        "nome": "Rio Verde",
        "estado": "Goiás", "pais": "Brasil", "iso": "BR",
        "lat": -17.7980, "lon": -50.9269,
        "culturas": ["soja", "milho", "sorgo", "pecuária"],
        "especialidade": "grãos+pecuária",
        "area_mha": 0.8,
        "volume_ref_mt": 2.8,
        "descricao": "Capital do agronegócio goiano",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_jatai",
        "nome": "Jataí",
        "estado": "Goiás", "pais": "Brasil", "iso": "BR",
        "lat": -17.8793, "lon": -51.7156,
        "culturas": ["soja", "milho", "sorgo"],
        "especialidade": "grãos",
        "area_mha": 0.7,
        "volume_ref_mt": 2.4,
        "descricao": "Polo milho-safrinha e soja no sudoeste goiano",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_dourados",
        "nome": "Dourados",
        "estado": "Mato Grosso do Sul", "pais": "Brasil", "iso": "BR",
        "lat": -22.2211, "lon": -54.8056,
        "culturas": ["soja", "milho", "cana"],
        "especialidade": "grãos",
        "area_mha": 0.6,
        "volume_ref_mt": 2.1,
        "descricao": "Principal polo agrícola de MS",
        "ceasa_ref": "ceasa_go",
    },

    # =========================================================
    # BRASIL — Nordeste / MATOPIBA
    # =========================================================
    {
        "id": "br_luis_eduardo_magalhaes",
        "nome": "Luís Eduardo Magalhães",
        "estado": "Bahia", "pais": "Brasil", "iso": "BR",
        "lat": -12.0961, "lon": -45.7897,
        "culturas": ["soja", "algodão", "milho"],
        "especialidade": "grãos+cerrado",
        "area_mha": 0.9,
        "volume_ref_mt": 3.2,
        "descricao": "Capital do Oeste baiano — polo MATOPIBA",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_barreiras",
        "nome": "Barreiras",
        "estado": "Bahia", "pais": "Brasil", "iso": "BR",
        "lat": -12.1521, "lon": -44.9938,
        "culturas": ["soja", "milho", "algodão", "café"],
        "especialidade": "grãos",
        "area_mha": 0.7,
        "volume_ref_mt": 2.5,
        "descricao": "Hub do cerrado baiano com aeroporto de cargas",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_balsas",
        "nome": "Balsas",
        "estado": "Maranhão", "pais": "Brasil", "iso": "BR",
        "lat": -7.5324, "lon": -46.0356,
        "culturas": ["soja", "milho"],
        "especialidade": "grãos+fronteira",
        "area_mha": 0.6,
        "volume_ref_mt": 2.0,
        "descricao": "80% da produção estadual — fronteira MATOPIBA",
        "ceasa_ref": "ceasa_go",
    },
    {
        "id": "br_paragominas",
        "nome": "Paragominas",
        "estado": "Pará", "pais": "Brasil", "iso": "BR",
        "lat": -2.9968, "lon": -47.3558,
        "culturas": ["soja", "milho", "pecuária"],
        "especialidade": "grãos+sustentabilidade",
        "area_mha": 0.4,
        "volume_ref_mt": 1.4,
        "descricao": "Referência em agricultura sustentável na Amazônia",
        "ceasa_ref": "ceasa_go",
    },

    # =========================================================
    # BRASIL — Vale do São Francisco (Fruticultura Irrigada)
    # =========================================================
    {
        "id": "br_petrolina",
        "nome": "Petrolina",
        "estado": "Pernambuco", "pais": "Brasil", "iso": "BR",
        "lat": -9.3973, "lon": -40.5010,
        "culturas": ["uva", "manga", "melão", "tomate"],
        "especialidade": "fruticultura_irrigada",
        "area_mha": 0.15,
        "volume_ref_mt": 0.8,
        "descricao": "Maior polo de fruticultura irrigada do Brasil",
        "ceasa_ref": "ceasa_rn",
    },
    {
        "id": "br_juazeiro",
        "nome": "Juazeiro",
        "estado": "Bahia", "pais": "Brasil", "iso": "BR",
        "lat": -9.4278, "lon": -40.5020,
        "culturas": ["uva", "manga", "cebola", "pimentão"],
        "especialidade": "fruticultura_irrigada",
        "area_mha": 0.14,
        "volume_ref_mt": 0.75,
        "descricao": "Polo VSF — maior exportador de uva do Brasil",
        "ceasa_ref": "ceasa_rn",
    },
    {
        "id": "br_mossoro",
        "nome": "Mossoró",
        "estado": "Rio Grande do Norte", "pais": "Brasil", "iso": "BR",
        "lat": -5.1878, "lon": -37.3444,
        "culturas": ["melão", "melancia", "abóbora"],
        "especialidade": "horticultura",
        "area_mha": 0.08,
        "volume_ref_mt": 0.5,
        "descricao": "Maior polo de melão do Brasil — exportação para Europa",
        "ceasa_ref": "ceasa_rn",
    },

    # =========================================================
    # BRASIL — Sul (Grãos, Aves, Suínos)
    # =========================================================
    {
        "id": "br_cascavel",
        "nome": "Cascavel",
        "estado": "Paraná", "pais": "Brasil", "iso": "BR",
        "lat": -24.9555, "lon": -53.4552,
        "culturas": ["soja", "milho", "trigo", "suínos"],
        "especialidade": "grãos+aves",
        "area_mha": 0.5,
        "volume_ref_mt": 1.8,
        "descricao": "Capital do agronegócio paranaense",
        "ceasa_ref": "ceasa_mg",
    },
    {
        "id": "br_londrina",
        "nome": "Londrina",
        "estado": "Paraná", "pais": "Brasil", "iso": "BR",
        "lat": -23.3045, "lon": -51.1696,
        "culturas": ["soja", "milho", "café", "trigo"],
        "especialidade": "grãos+pesquisa",
        "area_mha": 0.4,
        "volume_ref_mt": 1.5,
        "descricao": "Sede Embrapa Soja — referência científica",
        "ceasa_ref": "ceasa_mg",
    },
    {
        "id": "br_maringa",
        "nome": "Maringá",
        "estado": "Paraná", "pais": "Brasil", "iso": "BR",
        "lat": -23.4205, "lon": -51.9333,
        "culturas": ["soja", "milho", "café", "mandioca"],
        "especialidade": "grãos",
        "area_mha": 0.4,
        "volume_ref_mt": 1.4,
        "descricao": "Hub regional de grãos norte-paranaense",
        "ceasa_ref": "ceasa_mg",
    },
    {
        "id": "br_passo_fundo",
        "nome": "Passo Fundo",
        "estado": "Rio Grande do Sul", "pais": "Brasil", "iso": "BR",
        "lat": -28.2620, "lon": -52.4064,
        "culturas": ["soja", "trigo", "milho", "aveia"],
        "especialidade": "grãos+trigo",
        "area_mha": 0.5,
        "volume_ref_mt": 1.7,
        "descricao": "Capital nacional do trigo — Embrapa Trigo",
        "ceasa_ref": "ceasa_mg",
    },

    # =========================================================
    # BRASIL — Sudeste (Café, Cana, Laranja, Hortifrutis)
    # =========================================================
    {
        "id": "br_ribeirao_preto",
        "nome": "Ribeirão Preto",
        "estado": "São Paulo", "pais": "Brasil", "iso": "BR",
        "lat": -21.1767, "lon": -47.8208,
        "culturas": ["cana", "laranja", "café"],
        "especialidade": "cana+citrus",
        "area_mha": 0.6,
        "volume_ref_mt": 4.0,
        "descricao": "Capital mundial do agronegócio — etanol e sucrose",
        "ceasa_ref": "ceasa_mg",
    },
    {
        "id": "br_franca",
        "nome": "Franca",
        "estado": "São Paulo", "pais": "Brasil", "iso": "BR",
        "lat": -20.5385, "lon": -47.4008,
        "culturas": ["café", "cana"],
        "especialidade": "café",
        "area_mha": 0.2,
        "volume_ref_mt": 0.6,
        "descricao": "Polo cafeeiro SP — café arábica premiado",
        "ceasa_ref": "ceasa_mg",
    },
    {
        "id": "br_patrocinio",
        "nome": "Patrocínio",
        "estado": "Minas Gerais", "pais": "Brasil", "iso": "BR",
        "lat": -18.9429, "lon": -46.9939,
        "culturas": ["café", "soja", "milho"],
        "especialidade": "café+grãos",
        "area_mha": 0.25,
        "volume_ref_mt": 0.5,
        "descricao": "Triângulo Mineiro — maior produtor de café do Brasil",
        "ceasa_ref": "ceasa_mg",
    },
    {
        "id": "br_campinas",
        "nome": "Campinas",
        "estado": "São Paulo", "pais": "Brasil", "iso": "BR",
        "lat": -22.9056, "lon": -47.0608,
        "culturas": ["laranja", "cana", "hortifrutis"],
        "especialidade": "hortifrutis+pesquisa",
        "area_mha": 0.15,
        "volume_ref_mt": 0.8,
        "descricao": "IAC — maior centro de pesquisa agrícola da América Latina",
        "ceasa_ref": "ceasa_mg",
    },

    # =========================================================
    # BRASIL — Pecuária
    # =========================================================
    {
        "id": "br_xinguara",
        "nome": "Xinguara",
        "estado": "Pará", "pais": "Brasil", "iso": "BR",
        "lat": -7.1000, "lon": -49.9500,
        "culturas": ["pecuária", "soja"],
        "especialidade": "pecuária",
        "area_mha": 1.2,
        "volume_ref_mt": 0.4,
        "descricao": "Sul do Pará — rebanho bovino recordista",
        "ceasa_ref": "ceasa_go",
    },

    # =========================================================
    # ARGENTINA — Pampa Húmeda
    # =========================================================
    {
        "id": "ar_rosario",
        "nome": "Rosario",
        "estado": "Santa Fe", "pais": "Argentina", "iso": "AR",
        "lat": -32.9442, "lon": -60.6505,
        "culturas": ["soja", "trigo", "milho", "girassol"],
        "especialidade": "grãos+porto",
        "area_mha": 2.0,
        "volume_ref_mt": 8.0,
        "descricao": "Maior porto graneleiro da América Latina — Up-River",
        "ceasa_ref": None,
    },
    {
        "id": "ar_cordoba",
        "nome": "Córdoba",
        "estado": "Córdoba", "pais": "Argentina", "iso": "AR",
        "lat": -31.4201, "lon": -64.1888,
        "culturas": ["soja", "milho", "trigo", "maní"],
        "especialidade": "grãos+pecuária",
        "area_mha": 1.5,
        "volume_ref_mt": 5.5,
        "descricao": "Segunda maior região produtora da Argentina",
        "ceasa_ref": None,
    },
    {
        "id": "ar_pergamino",
        "nome": "Pergamino",
        "estado": "Buenos Aires", "pais": "Argentina", "iso": "AR",
        "lat": -33.8882, "lon": -60.5704,
        "culturas": ["soja", "milho", "trigo"],
        "especialidade": "grãos",
        "area_mha": 0.8,
        "volume_ref_mt": 2.8,
        "descricao": "Triângulo agrário — maior produtividade por ha da Argentina",
        "ceasa_ref": None,
    },
    {
        "id": "ar_venado_tuerto",
        "nome": "Venado Tuerto",
        "estado": "Santa Fe", "pais": "Argentina", "iso": "AR",
        "lat": -33.7454, "lon": -61.9684,
        "culturas": ["soja", "milho", "trigo", "girassol"],
        "especialidade": "grãos",
        "area_mha": 0.7,
        "volume_ref_mt": 2.5,
        "descricao": "Vértice sul do triângulo agrário",
        "ceasa_ref": None,
    },
    {
        "id": "ar_bahia_blanca",
        "nome": "Bahía Blanca",
        "estado": "Buenos Aires", "pais": "Argentina", "iso": "AR",
        "lat": -38.7183, "lon": -62.2663,
        "culturas": ["trigo", "girassol", "cevada"],
        "especialidade": "grãos+porto",
        "area_mha": 0.9,
        "volume_ref_mt": 3.0,
        "descricao": "Porto sul — exportação de trigo para Europa e Ásia",
        "ceasa_ref": None,
    },
    {
        "id": "ar_tucuman",
        "nome": "Tucumán",
        "estado": "Tucumán", "pais": "Argentina", "iso": "AR",
        "lat": -26.8241, "lon": -65.2226,
        "culturas": ["cana", "limão", "tabaco", "soja"],
        "especialidade": "cana+citrus",
        "area_mha": 0.3,
        "volume_ref_mt": 1.8,
        "descricao": "Maior produtor de cana e limão da Argentina",
        "ceasa_ref": None,
    },
    {
        "id": "ar_mendoza",
        "nome": "Mendoza",
        "estado": "Mendoza", "pais": "Argentina", "iso": "AR",
        "lat": -32.8908, "lon": -68.8272,
        "culturas": ["uva", "vinho", "azeite", "alho"],
        "especialidade": "vitivinicultura",
        "area_mha": 0.15,
        "volume_ref_mt": 0.9,
        "descricao": "Capital mundial da vitivinicultura sul-americana",
        "ceasa_ref": None,
    },
    {
        "id": "ar_salta",
        "nome": "Salta",
        "estado": "Salta", "pais": "Argentina", "iso": "AR",
        "lat": -24.7859, "lon": -65.4116,
        "culturas": ["soja", "tabaco", "pimentão", "feijão"],
        "especialidade": "grãos+hortifrutis",
        "area_mha": 0.5,
        "volume_ref_mt": 1.5,
        "descricao": "Expansão rápida de soja no noroeste argentino",
        "ceasa_ref": None,
    },

    # =========================================================
    # PARAGUAI
    # =========================================================
    {
        "id": "py_alto_parana",
        "nome": "Alto Paraná",
        "estado": "Alto Paraná", "pais": "Paraguai", "iso": "PY",
        "lat": -25.5094, "lon": -54.6100,
        "culturas": ["soja", "milho", "trigo"],
        "especialidade": "grãos",
        "area_mha": 1.2,
        "volume_ref_mt": 4.0,
        "descricao": "Maior polo sojeiro do Paraguai — fronteira com Brasil",
        "ceasa_ref": None,
    },
    {
        "id": "py_itapua",
        "nome": "Itapúa",
        "estado": "Itapúa", "pais": "Paraguai", "iso": "PY",
        "lat": -27.3326, "lon": -55.8666,
        "culturas": ["soja", "trigo", "milho", "erva-mate"],
        "especialidade": "grãos+erva",
        "area_mha": 0.8,
        "volume_ref_mt": 2.5,
        "descricao": "Sul do Paraguai — polo misto grãos e erva-mate",
        "ceasa_ref": None,
    },
    {
        "id": "py_caaguazu",
        "nome": "Caaguazú",
        "estado": "Caaguazú", "pais": "Paraguai", "iso": "PY",
        "lat": -25.4367, "lon": -56.0194,
        "culturas": ["soja", "milho", "trigo"],
        "especialidade": "grãos",
        "area_mha": 0.6,
        "volume_ref_mt": 2.0,
        "descricao": "Região de expansão agrícola no centro do Paraguai",
        "ceasa_ref": None,
    },

    # =========================================================
    # URUGUAI
    # =========================================================
    {
        "id": "uy_paysandu",
        "nome": "Paysandú",
        "estado": "Paysandú", "pais": "Uruguai", "iso": "UY",
        "lat": -32.3220, "lon": -58.0756,
        "culturas": ["soja", "trigo", "milho", "arroz"],
        "especialidade": "grãos",
        "area_mha": 0.4,
        "volume_ref_mt": 1.2,
        "descricao": "Polo agrícola do noroeste uruguaio",
        "ceasa_ref": None,
    },
    {
        "id": "uy_rivera",
        "nome": "Rivera",
        "estado": "Rivera", "pais": "Uruguai", "iso": "UY",
        "lat": -30.9020, "lon": -55.5500,
        "culturas": ["soja", "pecuária", "florestal"],
        "especialidade": "grãos+pecuária",
        "area_mha": 0.3,
        "volume_ref_mt": 0.8,
        "descricao": "Fronteira BR-UY — produção integrada",
        "ceasa_ref": None,
    },

    # =========================================================
    # BOLÍVIA
    # =========================================================
    {
        "id": "bo_santa_cruz",
        "nome": "Santa Cruz de la Sierra",
        "estado": "Santa Cruz", "pais": "Bolívia", "iso": "BO",
        "lat": -17.7833, "lon": -63.1821,
        "culturas": ["soja", "girassol", "sorgo", "milho"],
        "especialidade": "grãos",
        "area_mha": 1.5,
        "volume_ref_mt": 4.5,
        "descricao": "90% da produção agrícola boliviana — expansão acelerada",
        "ceasa_ref": None,
    },

    # =========================================================
    # PERU
    # =========================================================
    {
        "id": "pe_ica",
        "nome": "Ica",
        "estado": "Ica", "pais": "Peru", "iso": "PE",
        "lat": -14.0678, "lon": -75.7286,
        "culturas": ["uva", "aspargo", "algodão", "tomate"],
        "especialidade": "agroexportação",
        "area_mha": 0.1,
        "volume_ref_mt": 0.4,
        "descricao": "Maior polo de agroexportação do Peru — frutas e vegetais",
        "ceasa_ref": None,
    },
    {
        "id": "pe_piura",
        "nome": "Piura",
        "estado": "Piura", "pais": "Peru", "iso": "PE",
        "lat": -5.1945, "lon": -80.6328,
        "culturas": ["manga", "limão", "banana", "algodão"],
        "especialidade": "fruticultura",
        "area_mha": 0.12,
        "volume_ref_mt": 0.5,
        "descricao": "Maior exportador de manga do hemisfério sul",
        "ceasa_ref": None,
    },

    # =========================================================
    # COLÔMBIA
    # =========================================================
    {
        "id": "co_llanos_orientales",
        "nome": "Llanos Orientales",
        "estado": "Meta", "pais": "Colômbia", "iso": "CO",
        "lat": 4.1531, "lon": -73.6347,
        "culturas": ["arroz", "milho", "palma", "pecuária"],
        "especialidade": "grãos+pecuária",
        "area_mha": 0.8,
        "volume_ref_mt": 1.8,
        "descricao": "Maior fronteira agrícola da Colômbia",
        "ceasa_ref": None,
    },
    {
        "id": "co_magdalena",
        "nome": "Santa Marta / Valle del Magdalena",
        "estado": "Magdalena", "pais": "Colômbia", "iso": "CO",
        "lat": 11.2404, "lon": -74.2110,
        "culturas": ["banana", "palma", "café"],
        "especialidade": "fruticultura+café",
        "area_mha": 0.2,
        "volume_ref_mt": 0.7,
        "descricao": "Maior polo de banana Cavendish para exportação",
        "ceasa_ref": None,
    },

    # =========================================================
    # VENEZUELA
    # =========================================================
    {
        "id": "ve_llanos",
        "nome": "Llanos Ocidentais",
        "estado": "Barinas", "pais": "Venezuela", "iso": "VE",
        "lat": 8.6230, "lon": -70.2079,
        "culturas": ["milho", "arroz", "sorgo", "pecuária"],
        "especialidade": "grãos+pecuária",
        "area_mha": 0.6,
        "volume_ref_mt": 1.2,
        "descricao": "Planície dos Llanos — principal região agrícola venezuelana",
        "ceasa_ref": None,
    },

    # =========================================================
    # CHILE
    # =========================================================
    {
        "id": "cl_valle_central",
        "nome": "Valle Central",
        "estado": "O'Higgins / Maule", "pais": "Chile", "iso": "CL",
        "lat": -34.5755, "lon": -71.0022,
        "culturas": ["uva", "cereja", "maçã", "paltas", "vinho"],
        "especialidade": "fruticultura+vitivinicultura",
        "area_mha": 0.3,
        "volume_ref_mt": 1.5,
        "descricao": "Maior exportador de cereja do hemisfério sul",
        "ceasa_ref": None,
    },
    {
        "id": "cl_atacama_horticultura",
        "nome": "Valle de Atacama",
        "estado": "Atacama", "pais": "Chile", "iso": "CL",
        "lat": -27.3668, "lon": -70.3313,
        "culturas": ["uva de mesa", "azeitona", "pimentão"],
        "especialidade": "fruticultura_irrigada",
        "area_mha": 0.08,
        "volume_ref_mt": 0.25,
        "descricao": "Produção irrigada de alta precisão no deserto",
        "ceasa_ref": None,
    },

    # =========================================================
    # EQUADOR
    # =========================================================
    {
        "id": "ec_guayas",
        "nome": "Guayas",
        "estado": "Guayas", "pais": "Equador", "iso": "EC",
        "lat": -2.1893, "lon": -79.8875,
        "culturas": ["banana", "cacao", "camarão", "arroz"],
        "especialidade": "banana+cacao",
        "area_mha": 0.25,
        "volume_ref_mt": 2.0,
        "descricao": "Maior exportador de banana do mundo",
        "ceasa_ref": None,
    },
]

# ---------------------------------------------------------------------------
# Índice rápido por país para filtragem
# ---------------------------------------------------------------------------
POLOS_POR_PAIS = {}
for p in POLOS_SA:
    POLOS_POR_PAIS.setdefault(p["iso"], []).append(p)

# ---------------------------------------------------------------------------
# Índice por especialidade
# ---------------------------------------------------------------------------
POLOS_POR_CULTURA = {}
for p in POLOS_SA:
    for cultura in p["culturas"]:
        POLOS_POR_CULTURA.setdefault(cultura, []).append(p["id"])

# Estatísticas
TOTAL_POLOS = len(POLOS_SA)
PAISES = list(POLOS_POR_PAIS.keys())
