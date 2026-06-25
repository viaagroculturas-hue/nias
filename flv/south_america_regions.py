"""
NIAS — Núcleo de Inteligência Agrocomercial da América do Sul
Configuração central de regiões e polos monitorados no continente.
"""

SCOPE = "south_america"
SCOPE_LABEL = "América do Sul"
SYSTEM_FULL_NAME = "NIAS — Núcleo de Inteligência Agrocomercial da América do Sul"

# ═══════════════════════════════════════════════════════════════════
# PAÍSES MONITORADOS
# ═══════════════════════════════════════════════════════════════════

MONITORED_COUNTRIES = {
    "BR": {"name": "Brasil",    "name_en": "Brazil",   "continent": "South America"},
    "AR": {"name": "Argentina", "name_en": "Argentina","continent": "South America"},
    "CL": {"name": "Chile",     "name_en": "Chile",    "continent": "South America"},
    "PE": {"name": "Peru",      "name_en": "Peru",     "continent": "South America"},
    "BO": {"name": "Bolívia",   "name_en": "Bolivia",  "continent": "South America"},
    "PY": {"name": "Paraguai",  "name_en": "Paraguay", "continent": "South America"},
    "UY": {"name": "Uruguai",   "name_en": "Uruguay",  "continent": "South America"},
    "CO": {"name": "Colômbia",  "name_en": "Colombia", "continent": "South America"},
    "EC": {"name": "Equador",   "name_en": "Ecuador",  "continent": "South America"},
}

# ═══════════════════════════════════════════════════════════════════
# POLOS PRODUTIVOS — estrutura padronizada para toda a América do Sul
# ═══════════════════════════════════════════════════════════════════

SOUTH_AMERICA_REGIONS = [

    # ─────────────────────────────────────────────────────────────
    # BRASIL — Núcleo operacional do NIAS
    # ─────────────────────────────────────────────────────────────
    {
        "id": "BR-SP-CIN",
        "country": "Brazil", "country_code": "BR",
        "region": "Cinturão Verde SP",
        "state_or_department": "SP",
        "city": "Mogi das Cruzes",
        "lat": -23.52, "lon": -46.19,
        "products": ["tomate", "alface", "pepino", "cebolinha", "pimentão"],
        "importance": "muito_alta",
        "notes": "Maior polo hortícola próximo à RMSP",
    },
    {
        "id": "BR-MG-SUL",
        "country": "Brazil", "country_code": "BR",
        "region": "Sul de Minas",
        "state_or_department": "MG",
        "city": "Pouso Alegre",
        "lat": -22.23, "lon": -45.93,
        "products": ["tomate", "batata", "café", "morango", "repolho"],
        "importance": "alta",
        "notes": "Polo de café e hortaliças temperadas",
    },
    {
        "id": "BR-MG-TRI",
        "country": "Brazil", "country_code": "BR",
        "region": "Triângulo Mineiro / Alto Paranaíba",
        "state_or_department": "MG",
        "city": "Uberaba",
        "lat": -19.75, "lon": -47.93,
        "products": ["soja", "milho", "cana", "tomate industrial"],
        "importance": "alta",
        "notes": "Grãos e tomate industrial para processamento",
    },
    {
        "id": "BR-GO-CRI",
        "country": "Brazil", "country_code": "BR",
        "region": "Cristalina GO",
        "state_or_department": "GO",
        "city": "Cristalina",
        "lat": -16.77, "lon": -47.61,
        "products": ["batata", "cebola", "alho", "soja"],
        "importance": "alta",
        "notes": "Maior produtor de batata do Brasil sob irrigação",
    },
    {
        "id": "BR-BA-VSF",
        "country": "Brazil", "country_code": "BR",
        "region": "Vale do São Francisco",
        "state_or_department": "BA",
        "city": "Juazeiro",
        "lat": -9.41, "lon": -40.50,
        "products": ["manga", "uva", "goiaba", "melão", "cebola"],
        "importance": "muito_alta",
        "notes": "Principal polo de fruticultura irrigada do NE",
    },
    {
        "id": "BR-BA-CHA",
        "country": "Brazil", "country_code": "BR",
        "region": "Chapada Diamantina",
        "state_or_department": "BA",
        "city": "Mucugê",
        "lat": -13.00, "lon": -41.37,
        "products": ["café", "alho", "batata", "cebola"],
        "importance": "media",
        "notes": "Alho e hortaliças de altitude",
    },
    {
        "id": "BR-CE-IBI",
        "country": "Brazil", "country_code": "BR",
        "region": "Ibiapaba CE",
        "state_or_department": "CE",
        "city": "Tianguá",
        "lat": -3.72, "lon": -40.99,
        "products": ["morango", "repolho", "batata", "cenoura"],
        "importance": "media",
        "notes": "Microclima serrano viabiliza hortaliças no semiárido",
    },
    {
        "id": "BR-RS-SGR",
        "country": "Brazil", "country_code": "BR",
        "region": "Serra Gaúcha",
        "state_or_department": "RS",
        "city": "Caxias do Sul",
        "lat": -29.17, "lon": -51.18,
        "products": ["uva", "maçã", "morango", "kiwi"],
        "importance": "alta",
        "notes": "Principal polo vitivinícola do Brasil",
    },
    {
        "id": "BR-SC-SER",
        "country": "Brazil", "country_code": "BR",
        "region": "Serra Catarinense",
        "state_or_department": "SC",
        "city": "Lages",
        "lat": -27.81, "lon": -50.33,
        "products": ["maçã", "pera", "alho", "cebola"],
        "importance": "alta",
        "notes": "Polo de maçã e alho de altitude",
    },
    {
        "id": "BR-SC-ITJ",
        "country": "Brazil", "country_code": "BR",
        "region": "Vale do Itajaí",
        "state_or_department": "SC",
        "city": "Ituporanga",
        "lat": -27.40, "lon": -49.59,
        "products": ["cebola", "alho", "batata"],
        "importance": "alta",
        "notes": "Maior polo de cebola do Brasil",
    },
    {
        "id": "BR-PR-HOT",
        "country": "Brazil", "country_code": "BR",
        "region": "Paraná hortícola",
        "state_or_department": "PR",
        "city": "Guarapuava",
        "lat": -25.39, "lon": -51.46,
        "products": ["batata", "soja", "milho", "alho"],
        "importance": "alta",
        "notes": "Segundo maior produtor de batata do Brasil",
    },
    {
        "id": "BR-MT-GRA",
        "country": "Brazil", "country_code": "BR",
        "region": "Mato Grosso",
        "state_or_department": "MT",
        "city": "Sorriso",
        "lat": -12.54, "lon": -55.72,
        "products": ["soja", "milho", "algodão", "sorgo"],
        "importance": "muito_alta",
        "notes": "Maior produtor de soja do mundo",
    },
    {
        "id": "BR-MA-MAT",
        "country": "Brazil", "country_code": "BR",
        "region": "MATOPIBA",
        "state_or_department": "MA",
        "city": "Balsas",
        "lat": -7.53, "lon": -46.04,
        "products": ["soja", "milho", "algodão"],
        "importance": "muito_alta",
        "notes": "Nova fronteira agrícola MA/TO/PI/BA",
    },
    {
        "id": "BR-RO-AMZ",
        "country": "Brazil", "country_code": "BR",
        "region": "Rondônia / Amazônia agrícola",
        "state_or_department": "RO",
        "city": "Ji-Paraná",
        "lat": -10.88, "lon": -61.94,
        "products": ["soja", "milho", "café robusta", "cacau"],
        "importance": "media",
        "notes": "Expansão agrícola com logística desafiadora",
    },

    # ─────────────────────────────────────────────────────────────
    # ARGENTINA
    # ─────────────────────────────────────────────────────────────
    {
        "id": "AR-MDZ-CEN",
        "country": "Argentina", "country_code": "AR",
        "region": "Mendoza",
        "state_or_department": "Mendoza",
        "city": "Mendoza",
        "lat": -32.89, "lon": -68.84,
        "products": ["uva", "alho", "cebola", "ameixa", "pêssego"],
        "importance": "muito_alta",
        "notes": "Principal polo de uva, alho e cebola da Argentina. Exportador regional.",
    },
    {
        "id": "AR-RIO-NEG",
        "country": "Argentina", "country_code": "AR",
        "region": "Río Negro / Neuquén",
        "state_or_department": "Río Negro",
        "city": "General Roca",
        "lat": -39.03, "lon": -67.58,
        "products": ["maçã", "pera", "mirtilo", "cereja"],
        "importance": "alta",
        "notes": "Vale do Rio Negro — maior produtor de maçã e pera do Cone Sul",
    },
    {
        "id": "AR-BUE-HOR",
        "country": "Argentina", "country_code": "AR",
        "region": "Buenos Aires / La Plata",
        "state_or_department": "Buenos Aires",
        "city": "La Plata",
        "lat": -34.92, "lon": -57.95,
        "products": ["tomate", "alface", "espinafre", "abobrinha"],
        "importance": "alta",
        "notes": "Cinturão hortícola do Grande Buenos Aires",
    },
    {
        "id": "AR-COR-GRA",
        "country": "Argentina", "country_code": "AR",
        "region": "Córdoba / Santa Fe",
        "state_or_department": "Córdoba",
        "city": "Córdoba",
        "lat": -31.42, "lon": -64.18,
        "products": ["soja", "milho", "girassol", "trigo"],
        "importance": "muito_alta",
        "notes": "Coração da agricultura pampeana. Porto Rosário.",
    },
    {
        "id": "AR-NOA-CIT",
        "country": "Argentina", "country_code": "AR",
        "region": "NOA — Noroeste Argentino",
        "state_or_department": "Tucumán",
        "city": "Tucumán",
        "lat": -26.82, "lon": -65.22,
        "products": ["limão", "cana-de-açúcar", "pimentão", "tomate"],
        "importance": "alta",
        "notes": "Maior produtor mundial de limão. Exportação para Europa.",
    },

    # ─────────────────────────────────────────────────────────────
    # CHILE
    # ─────────────────────────────────────────────────────────────
    {
        "id": "CL-RMS-EXP",
        "country": "Chile", "country_code": "CL",
        "region": "Região Metropolitana / Valparaíso",
        "state_or_department": "Valparaíso",
        "city": "Valparaíso",
        "lat": -33.04, "lon": -71.62,
        "products": ["abacate", "cítricos", "tomate", "uva"],
        "importance": "alta",
        "notes": "Hub de exportação portuária. Abacate Hass para Europa e EUA.",
    },
    {
        "id": "CL-OHI-FRU",
        "country": "Chile", "country_code": "CL",
        "region": "O'Higgins / Maule",
        "state_or_department": "O'Higgins",
        "city": "Rancagua",
        "lat": -34.17, "lon": -70.74,
        "products": ["uva", "cereja", "maçã", "pêra", "kiwi"],
        "importance": "muito_alta",
        "notes": "Maior exportador de cereja e uva do Hemisfério Sul",
    },
    {
        "id": "CL-COQ-UVA",
        "country": "Chile", "country_code": "CL",
        "region": "Coquimbo",
        "state_or_department": "Coquimbo",
        "city": "La Serena",
        "lat": -29.91, "lon": -71.25,
        "products": ["uva", "cítricos", "pimentão", "tomate"],
        "importance": "media",
        "notes": "Uva de mesa e cítricos para exportação precoce",
    },
    {
        "id": "CL-BIO-GRA",
        "country": "Chile", "country_code": "CL",
        "region": "Biobío / Araucanía",
        "state_or_department": "Biobío",
        "city": "Concepción",
        "lat": -36.82, "lon": -73.05,
        "products": ["trigo", "aveia", "maçã", "mirtilo"],
        "importance": "media",
        "notes": "Clima frio — grãos e frutas temperadas",
    },

    # ─────────────────────────────────────────────────────────────
    # PERU
    # ─────────────────────────────────────────────────────────────
    {
        "id": "PE-ICA-EXP",
        "country": "Peru", "country_code": "PE",
        "region": "Ica",
        "state_or_department": "Ica",
        "city": "Ica",
        "lat": -14.07, "lon": -75.73,
        "products": ["uva", "mirtilo", "aspargo", "páprika"],
        "importance": "muito_alta",
        "notes": "Maior polo de agroexportação do Peru. Mirtilo #1 mundial.",
    },
    {
        "id": "PE-LIB-MIR",
        "country": "Peru", "country_code": "PE",
        "region": "La Libertad",
        "state_or_department": "La Libertad",
        "city": "Trujillo",
        "lat": -8.11, "lon": -79.03,
        "products": ["mirtilo", "abacate", "cana-de-açúcar", "aspargo"],
        "importance": "muito_alta",
        "notes": "Segundo polo de mirtilo. Abacate Hass para Europa.",
    },
    {
        "id": "PE-PIU-MAN",
        "country": "Peru", "country_code": "PE",
        "region": "Piura",
        "state_or_department": "Piura",
        "city": "Piura",
        "lat": -5.19, "lon": -80.63,
        "products": ["manga", "banana", "limão", "uva"],
        "importance": "alta",
        "notes": "Manga Kent para Europa e EUA. Janela de exportação contra-safra brasileira.",
    },
    {
        "id": "PE-ARE-HOR",
        "country": "Peru", "country_code": "PE",
        "region": "Arequipa",
        "state_or_department": "Arequipa",
        "city": "Arequipa",
        "lat": -16.41, "lon": -71.54,
        "products": ["cebola", "alho", "páprika", "alcachofra"],
        "importance": "alta",
        "notes": "Cebola e alho para Brasil. Exportação relevante no verão.",
    },

    # ─────────────────────────────────────────────────────────────
    # BOLÍVIA
    # ─────────────────────────────────────────────────────────────
    {
        "id": "BO-SCZ-GRA",
        "country": "Bolivia", "country_code": "BO",
        "region": "Santa Cruz de la Sierra",
        "state_or_department": "Santa Cruz",
        "city": "Santa Cruz de la Sierra",
        "lat": -17.78, "lon": -63.18,
        "products": ["soja", "milho", "girassol", "carne bovina"],
        "importance": "alta",
        "notes": "Pólo agroindustrial da Bolívia. Corredor com Brasil via Corumbá.",
    },
    {
        "id": "BO-COC-HOR",
        "country": "Bolivia", "country_code": "BO",
        "region": "Cochabamba",
        "state_or_department": "Cochabamba",
        "city": "Cochabamba",
        "lat": -17.39, "lon": -66.16,
        "products": ["batata", "milho", "cenoura", "cebola"],
        "importance": "media",
        "notes": "Hortaliças de altitude. Mercado interno boliviano.",
    },
    {
        "id": "BO-TAR-UVA",
        "country": "Bolivia", "country_code": "BO",
        "region": "Tarija",
        "state_or_department": "Tarija",
        "city": "Tarija",
        "lat": -21.53, "lon": -64.73,
        "products": ["uva", "maçã", "pêra", "pêssego"],
        "importance": "baixa",
        "notes": "Vitivinicultura boliviana. Frutas de clima temperado.",
    },

    # ─────────────────────────────────────────────────────────────
    # PARAGUAI
    # ─────────────────────────────────────────────────────────────
    {
        "id": "PY-APA-GRA",
        "country": "Paraguay", "country_code": "PY",
        "region": "Alto Paraná",
        "state_or_department": "Alto Paraná",
        "city": "Ciudad del Este",
        "lat": -25.51, "lon": -54.61,
        "products": ["soja", "milho", "trigo"],
        "importance": "alta",
        "notes": "Soja e milho integrados à logística brasileira. Fronteira com BR/AR.",
    },
    {
        "id": "PY-ITA-GRA",
        "country": "Paraguay", "country_code": "PY",
        "region": "Itapúa",
        "state_or_department": "Itapúa",
        "city": "Encarnación",
        "lat": -27.33, "lon": -55.87,
        "products": ["soja", "trigo", "carne bovina"],
        "importance": "media",
        "notes": "Grãos e pecuária. Fronteira com Argentina (Posadas).",
    },
    {
        "id": "PY-CEN-DIS",
        "country": "Paraguay", "country_code": "PY",
        "region": "Central / Asunción",
        "state_or_department": "Central",
        "city": "Asunción",
        "lat": -25.28, "lon": -57.63,
        "products": ["hortaliças", "frutas locais"],
        "importance": "media",
        "notes": "Centro de consumo e distribuição do Paraguai.",
    },

    # ─────────────────────────────────────────────────────────────
    # URUGUAI
    # ─────────────────────────────────────────────────────────────
    {
        "id": "UY-CAN-HOR",
        "country": "Uruguay", "country_code": "UY",
        "region": "Canelones",
        "state_or_department": "Canelones",
        "city": "Canelones",
        "lat": -34.52, "lon": -56.28,
        "products": ["tomate", "alface", "cebola", "uva"],
        "importance": "media",
        "notes": "Principal polo hortífrutícola do Uruguai.",
    },
    {
        "id": "UY-SAL-CIT",
        "country": "Uruguay", "country_code": "UY",
        "region": "Salto / Paysandú",
        "state_or_department": "Salto",
        "city": "Salto",
        "lat": -31.39, "lon": -57.96,
        "products": ["laranja", "tangerina", "limão", "carne bovina"],
        "importance": "media",
        "notes": "Citros para exportação. Pecuária de qualidade.",
    },
    {
        "id": "UY-MVD-POR",
        "country": "Uruguay", "country_code": "UY",
        "region": "Montevidéu",
        "state_or_department": "Montevideo",
        "city": "Montevideo",
        "lat": -34.90, "lon": -56.19,
        "products": ["distribuição", "consumo"],
        "importance": "media",
        "notes": "Porto e centro de distribuição. Saída marítima do MERCOSUL.",
    },

    # ─────────────────────────────────────────────────────────────
    # COLÔMBIA
    # ─────────────────────────────────────────────────────────────
    {
        "id": "CO-CUN-HOR",
        "country": "Colombia", "country_code": "CO",
        "region": "Cundinamarca / Bogotá",
        "state_or_department": "Cundinamarca",
        "city": "Bogotá",
        "lat": 4.71, "lon": -74.07,
        "products": ["batata", "cenoura", "repolho", "brócolis"],
        "importance": "media",
        "notes": "Hortaliças de altitude. Maior mercado consumidor da Colômbia.",
    },
    {
        "id": "CO-ANT-FRU",
        "country": "Colombia", "country_code": "CO",
        "region": "Antioquia",
        "state_or_department": "Antioquia",
        "city": "Medellín",
        "lat": 6.24, "lon": -75.57,
        "products": ["banana", "abacate", "tomate", "pimentão"],
        "importance": "media",
        "notes": "Frutas tropicais e hortaliças. Banana para exportação.",
    },
    {
        "id": "CO-VAL-CAN",
        "country": "Colombia", "country_code": "CO",
        "region": "Valle del Cauca",
        "state_or_department": "Valle del Cauca",
        "city": "Cali",
        "lat": 3.43, "lon": -76.52,
        "products": ["cana-de-açúcar", "frutas tropicais", "café"],
        "importance": "media",
        "notes": "Cana e agroindustria. Porto Buenaventura (Pacífico).",
    },

    # ─────────────────────────────────────────────────────────────
    # EQUADOR
    # ─────────────────────────────────────────────────────────────
    {
        "id": "EC-GUA-BAN",
        "country": "Ecuador", "country_code": "EC",
        "region": "Guayas",
        "state_or_department": "Guayas",
        "city": "Guayaquil",
        "lat": -2.19, "lon": -79.89,
        "products": ["banana", "cacau", "camarão"],
        "importance": "alta",
        "notes": "Maior exportador mundial de banana. Porto Guayaquil.",
    },
    {
        "id": "EC-ORO-BAN",
        "country": "Ecuador", "country_code": "EC",
        "region": "El Oro",
        "state_or_department": "El Oro",
        "city": "Machala",
        "lat": -3.26, "lon": -79.96,
        "products": ["banana", "cacao"],
        "importance": "alta",
        "notes": "Capital mundial da banana. Exportação massiva para Europa.",
    },
    {
        "id": "EC-PIC-HOR",
        "country": "Ecuador", "country_code": "EC",
        "region": "Sierra / Quito",
        "state_or_department": "Pichincha",
        "city": "Quito",
        "lat": -0.22, "lon": -78.51,
        "products": ["brócolis", "alcachofra", "morango", "batata"],
        "importance": "media",
        "notes": "Hortaliças de altitude exportadas para EUA e Europa.",
    },
]

# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def get_all_regions() -> list:
    return SOUTH_AMERICA_REGIONS


def get_regions_by_country(country_code: str) -> list:
    return [r for r in SOUTH_AMERICA_REGIONS if r["country_code"] == country_code.upper()]


def get_weather_points() -> list:
    """Retorna lista de coordenadas para batch Open-Meteo."""
    return [
        {"id": r["id"], "lat": r["lat"], "lon": r["lon"],
         "region": r["region"], "country_code": r["country_code"]}
        for r in SOUTH_AMERICA_REGIONS
    ]


def get_country_codes() -> list:
    return list(MONITORED_COUNTRIES.keys())


def get_region_by_id(region_id: str) -> dict | None:
    for r in SOUTH_AMERICA_REGIONS:
        if r["id"] == region_id:
            return r
    return None


def summary() -> dict:
    by_country = {}
    for r in SOUTH_AMERICA_REGIONS:
        cc = r["country_code"]
        by_country[cc] = by_country.get(cc, 0) + 1
    return {
        "scope": SCOPE,
        "scope_label": SCOPE_LABEL,
        "total_regions": len(SOUTH_AMERICA_REGIONS),
        "countries": len(by_country),
        "by_country": by_country,
        "monitored_countries": list(MONITORED_COUNTRIES.keys()),
    }
