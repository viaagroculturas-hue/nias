"""
NIAS South America Price Sources — mapa de fontes de preço por país.

Status possíveis:
  real          → fonte ativa, coletor implementado, dados reais disponíveis
  partial       → fonte real mas cobertura incompleta
  to_research   → fonte pública identificada, coletor ainda não implementado
  needs_auth    → fonte existe mas requer credenciais ou cadastro
  unavailable   → fonte investigada, sem acesso público adequado
  no_source     → país sem fonte adequada identificada

Access types:
  api           → API pública REST/JSON
  csv           → arquivo CSV público
  xlsx          → planilha Excel pública
  html_table    → tabela HTML parseável sem scraping agressivo
  manual        → download manual recorrente
  unavailable   → sem acesso automatizável
"""
from __future__ import annotations

SOUTH_AMERICA_PRICE_SOURCES: dict = {

    "BR": {
        "name": "Brasil",
        "currency": "BRL",
        "currency_symbol": "R$",
        "language": "pt",
        "status": "real",
        "sources": [
            {
                "name": "CONAB/PROHORT",
                "description": "Central Nacional de Abastecimento — Preços semanais por UF",
                "url": "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosSemanalUF.txt",
                "access_type": "csv",
                "legal_status": "official",
                "frequency": "weekly",
                "status": "real",
                "products": ["tomate", "cebola", "batata", "pimentao", "alface",
                             "cenoura", "manga", "uva", "banana", "laranja",
                             "morango", "maca", "melao", "mamao", "abacaxi", "alho"],
                "notes": "Fonte oficial primária Brasil — já implementada em flv/collectors/ceasa.py",
                "implemented": True,
                "collector_module": "flv.collectors.ceasa",
            },
        ],
        "products": ["tomate", "cebola", "batata", "banana", "laranja", "alho",
                     "manga", "uva", "cenoura", "pimentao", "morango"],
        "notes": "Brasil totalmente implementado. Não alterar.",
    },

    "AR": {
        "name": "Argentina",
        "currency": "ARS",
        "currency_symbol": "$",
        "language": "es",
        "status": "partial",
        "sources": [
            {
                "name": "Mercado Central de Buenos Aires",
                "description": "Preços diários no mercado concentrador principal da Argentina",
                "url": "https://www.mercadocentral.gob.ar/paginas/informacion-de-precios",
                "access_type": "html_table",
                "legal_status": "official",
                "frequency": "daily",
                "status": "real",
                "products": ["cebolla", "papa", "tomate", "ajo", "zanahoria",
                             "pimiento", "manzana", "pera", "uva", "naranja"],
                "notes": "Página HTML com tabela pública. Requer parse controlado sem scraping agressivo.",
                "implemented": True,
                "collector_module": "flv.collectors.prices.ar_prices",
            },
            {
                "name": "MAGyP — Ministerio de Agricultura",
                "description": "Estadísticas de precios agropecuarios",
                "url": "https://www.magyp.gob.ar/sitio/areas/ss_mercados_agropecuarios/",
                "access_type": "xlsx",
                "legal_status": "official",
                "frequency": "weekly",
                "status": "to_research",
                "products": ["granos", "frutas", "hortalizas"],
                "notes": "Planilhas XLS disponíveis mas estrutura variável. Monitorar.",
                "implemented": False,
            },
            {
                "name": "INDEC",
                "description": "Instituto Nacional de Estadística — IPC alimentos",
                "url": "https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-5-31",
                "access_type": "xlsx",
                "legal_status": "official",
                "frequency": "monthly",
                "status": "to_research",
                "products": ["alimentos em geral"],
                "notes": "IPC mensal — útil para deflator, não para preço no atacado.",
                "implemented": False,
            },
        ],
        "products": ["cebolla", "papa", "tomate", "ajo", "zanahoria", "manzana", "uva"],
        "notes": "Coletor implementado para Mercado Central BA via HTML table público.",
    },

    "CL": {
        "name": "Chile",
        "currency": "CLP",
        "currency_symbol": "$",
        "language": "es",
        "status": "real",
        "sources": [
            {
                "name": "ODEPA — Oficina de Estudios y Políticas Agrarias",
                "description": "Preços de frutas e hortaliças nos mercados chilenos",
                "url": "https://www.odepa.gob.cl/estadisticas-del-sector/estadisticas-productivas/informacion-de-precios",
                "access_type": "api",
                "legal_status": "official",
                "frequency": "weekly",
                "status": "real",
                "products": ["tomate", "cebolla", "papa", "ajo", "limon",
                             "manzana", "pera", "uva", "naranja", "palto"],
                "notes": "ODEPA tem API pública JSON. Endpoint: https://api.odepa.gob.cl/precios. Implementado.",
                "implemented": True,
                "collector_module": "flv.collectors.prices.cl_odepa",
            },
        ],
        "products": ["tomate", "cebolla", "papa", "ajo", "manzana", "pera", "uva", "palto"],
        "notes": "ODEPA é a fonte oficial mais estruturada da América do Sul.",
    },

    "PE": {
        "name": "Peru",
        "currency": "PEN",
        "currency_symbol": "S/",
        "language": "es",
        "status": "partial",
        "sources": [
            {
                "name": "MIDAGRI / SISAP",
                "description": "Sistema de Información de Abastecimiento y Precios",
                "url": "https://sistemas.midagri.gob.pe/sisap/portal2/mayorista/",
                "access_type": "html_table",
                "legal_status": "official",
                "frequency": "daily",
                "status": "real",
                "products": ["papa", "tomate", "cebolla", "ajo", "limón",
                             "naranja", "mango", "plátano", "uva"],
                "notes": "SISAP exibe preços nos mercados mayoristas de Lima (La Parada, Santa Anita). Parse HTML.",
                "implemented": True,
                "collector_module": "flv.collectors.prices.pe_midagri",
            },
        ],
        "products": ["papa", "tomate", "cebolla", "ajo", "mango", "platano"],
        "notes": "MIDAGRI SISAP: fonte pública oficial. Estrutura HTML estável.",
    },

    "UY": {
        "name": "Uruguai",
        "currency": "UYU",
        "currency_symbol": "$U",
        "language": "es",
        "status": "partial",
        "sources": [
            {
                "name": "Mercado Modelo / UAM",
                "description": "Unidad Administradora del Mercado Modelo — preços hortifrutícolas",
                "url": "https://www.mercadomodelo.net/precios",
                "access_type": "html_table",
                "legal_status": "official",
                "frequency": "daily",
                "status": "real",
                "products": ["tomate", "cebolla", "papa", "ajo", "naranja", "mandarina"],
                "notes": "Mercado Modelo tem boletim diário público.",
                "implemented": True,
                "collector_module": "flv.collectors.prices.uy_uam",
            },
            {
                "name": "MGAP — Ministerio de Ganadería, Agricultura y Pesca",
                "description": "Estadísticas agropecuarias",
                "url": "https://www.gub.uy/ministerio-ganaderia-agricultura-pesca/datos-y-estadisticas/estadisticas",
                "access_type": "xlsx",
                "legal_status": "official",
                "frequency": "monthly",
                "status": "to_research",
                "products": ["horticultura", "fruticultura"],
                "notes": "Dados mensais, mais útil para análise histórica.",
                "implemented": False,
            },
        ],
        "products": ["tomate", "cebolla", "papa", "naranja"],
        "notes": "Mercado Modelo é a referência de atacado hortifrutícola no Uruguai.",
    },

    "CO": {
        "name": "Colômbia",
        "currency": "COP",
        "currency_symbol": "$",
        "language": "es",
        "status": "real",
        "sources": [
            {
                "name": "SIPSA / DANE",
                "description": "Sistema de Información de Precios del Sector Agropecuario",
                "url": "https://www.dane.gov.co/index.php/estadisticas-por-tema/agropecuario/sistema-de-informacion-de-precios-sipsa",
                "access_type": "api",
                "legal_status": "official",
                "frequency": "weekly",
                "status": "real",
                "products": ["tomate", "cebolla", "papa", "platano", "aguacate",
                             "mango", "naranja", "zanahoria", "lechuga"],
                "notes": "DANE/SIPSA tem API pública e boletins CSV semanais.",
                "implemented": True,
                "collector_module": "flv.collectors.prices.co_sipsa",
            },
        ],
        "products": ["tomate", "cebolla", "papa", "platano", "aguacate", "mango"],
        "notes": "SIPSA é referência técnica para preços agro na Colômbia.",
    },

    "PY": {
        "name": "Paraguai",
        "currency": "PYG",
        "currency_symbol": "₲",
        "language": "es",
        "status": "to_research",
        "sources": [
            {
                "name": "MAG — Ministerio de Agricultura y Ganadería",
                "description": "DCEA — Dirección de Censos y Estadísticas Agropecuarias",
                "url": "https://www.mag.gov.py/dcea/",
                "access_type": "xlsx",
                "legal_status": "official",
                "frequency": "monthly",
                "status": "to_research",
                "products": ["soja", "maiz", "trigo", "mandioca", "tomate"],
                "notes": "Planilhas mensais. Estrutura a verificar. Foco em grãos, não hortifrutícola.",
                "implemented": False,
            },
            {
                "name": "Mercado de Abasto de Asunción",
                "description": "Preços no mercado de abastecimento de Assunção",
                "url": "https://www.mercadodeabasto.gov.py/",
                "access_type": "html_table",
                "legal_status": "official",
                "frequency": "daily",
                "status": "to_research",
                "products": ["tomate", "cebolla", "papa", "banana", "naranja"],
                "notes": "Site oficial a verificar disponibilidade de tabela de preços.",
                "implemented": False,
            },
        ],
        "products": ["tomate", "cebolla", "papa", "soja", "mandioca"],
        "notes": "Fontes identificadas mas ainda a verificar acesso. Foco inicial em MAG/DCEA.",
    },

    "EC": {
        "name": "Equador",
        "currency": "USD",
        "currency_symbol": "$",
        "language": "es",
        "status": "to_research",
        "sources": [
            {
                "name": "MAG — Ministerio de Agricultura y Ganadería",
                "description": "SIPA — Sistema de Información Pública Agropecuaria",
                "url": "https://sipa.agricultura.gob.ec/",
                "access_type": "api",
                "legal_status": "official",
                "frequency": "weekly",
                "status": "to_research",
                "products": ["papa", "tomate", "cebolla", "platano", "naranja", "mango"],
                "notes": "SIPA Ecuador usa USD (economia dolarizada). API a verificar.",
                "implemented": False,
            },
        ],
        "products": ["papa", "tomate", "platano", "cacao", "banano"],
        "notes": "Equador usa USD — facilita comparação regional. SIPA a pesquisar.",
    },

    "BO": {
        "name": "Bolívia",
        "currency": "BOB",
        "currency_symbol": "Bs.",
        "language": "es",
        "status": "no_source",
        "sources": [
            {
                "name": "MDRyT / OAP",
                "description": "Ministerio de Desarrollo Rural — Observatorio Agroambiental y Productivo",
                "url": "https://www.oap.agro.gov.bo/",
                "access_type": "html_table",
                "legal_status": "official",
                "frequency": "monthly",
                "status": "unavailable",
                "products": ["papa", "quinua", "maiz", "tomate"],
                "notes": "OAP existe mas acesso a dados de preços de mercado é limitado online.",
                "implemented": False,
            },
        ],
        "products": ["papa", "quinua", "maiz", "tomate"],
        "notes": "Sem fonte adequada identificada no momento. Retorna source_not_available.",
    },
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_source_config(country_code: str) -> dict:
    return SOUTH_AMERICA_PRICE_SOURCES.get(country_code.upper(), {})


def get_all_countries() -> list[str]:
    return list(SOUTH_AMERICA_PRICE_SOURCES.keys())


def get_implemented_countries() -> list[str]:
    """Países com ao menos um coletor implementado."""
    result = []
    for cc, cfg in SOUTH_AMERICA_PRICE_SOURCES.items():
        if any(s.get('implemented') for s in cfg.get('sources', [])):
            result.append(cc)
    return result


def get_status_summary() -> dict:
    """Resumo de status por país para o endpoint /api/nias/prices/status."""
    summary = {}
    for cc, cfg in SOUTH_AMERICA_PRICE_SOURCES.items():
        implemented_sources = [s for s in cfg.get('sources', []) if s.get('implemented')]
        summary[cc] = {
            'country': cfg.get('name', cc),
            'status': cfg.get('status', 'unknown'),
            'currency': cfg.get('currency'),
            'implemented_sources': len(implemented_sources),
            'total_sources': len(cfg.get('sources', [])),
            'products': cfg.get('products', []),
            'notes': cfg.get('notes', ''),
        }
    return summary
