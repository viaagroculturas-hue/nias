"""Situation Real API
Painel factual para Recuperação Judicial (RJ), produção agropecuária e impacto setorial.

Regra de confiabilidade:
- Não inventar valores em tempo real.
- Dado interno é marcado como "base_interna_validar".
- Fonte oficial conectável é marcada como "fonte_oficial".
- Quando uma API externa exige token/limite/indisponibilidade, o payload informa a limitação.
"""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATHS = [os.path.join(DIR, "nia_flv.db"), os.path.join(DIR, "flv", "nia_flv.db")]

OFFICIAL_SOURCES = [
    {
        "id": "cnj_datajud",
        "name": "CNJ DataJud API Pública",
        "scope": "metadados oficiais de processos judiciais no Brasil, incluindo classes de recuperação judicial e falência quando consultáveis",
        "url": "https://datajud-wiki.cnj.jus.br/api-publica/",
        "live_status": "requer API-Key/autorização e consulta por tribunal; não substituir por dado simulado",
        "use_in_panel": "validar existência, tribunal, classe processual, data da última movimentação e status processual"
    },
    {
        "id": "ibge_pam_sidra",
        "name": "IBGE PAM / SIDRA",
        "scope": "produção agrícola municipal anual por cultura, área, rendimento e valor da produção",
        "url": "https://www.ibge.gov.br/estatisticas/economicas/agricultura-e-pecuaria/9117-producao-agricola-municipal-culturas-temporarias-e-permanentes.html",
        "live_status": "oficial; atualização anual; adequado para base estrutural municipal",
        "use_in_panel": "estimar dependência produtiva local e impacto regional por cultura"
    },
    {
        "id": "ibge_lspa",
        "name": "IBGE LSPA",
        "scope": "estimativas mensais de safra, área e rendimento de produtos selecionados",
        "url": "https://www.ibge.gov.br/estatisticas/economicas/agricultura-e-pecuaria/9201-levantamento-sistematico-da-producao-agricola.html",
        "live_status": "oficial; atualização mensal; adequado para alerta de safra",
        "use_in_panel": "monitorar quebra de safra e variação de produção"
    },
    {
        "id": "conab_safra",
        "name": "CONAB Safras / Portal de Informações Agropecuárias",
        "scope": "safra de grãos, oferta e demanda, preços agropecuários, logística e hortigranjeiros/PROHORT",
        "url": "https://portaldeinformacoes.conab.gov.br/safra-serie-historica-graos.html",
        "live_status": "oficial; usar somente séries/boletins identificados por data",
        "use_in_panel": "validar risco de abastecimento em grãos, hortigranjeiros e logística"
    },
    {
        "id": "cepea_hfbrasil",
        "name": "CEPEA / HF Brasil",
        "scope": "preços agropecuários e séries de hortifrúti por produto, região e frequência",
        "url": "https://www.hfbrasil.org.br/br/banco-de-dados-precos-medios-dos-hortifruticolas.aspx",
        "live_status": "fonte técnica de mercado; algumas séries exigem consulta/download",
        "use_in_panel": "preço regional e pressão de margem"
    },
]

SECTOR_RULES = {
    "CANA_DE_ACUCAR": ["indústria sucroenergética", "etanol", "açúcar", "transporte rodoviário", "emprego rural sazonal"],
    "MILHO": ["ração animal", "avicultura", "suinocultura", "leite", "atacado alimentar", "frete e armazenagem"],
    "SOJA": ["exportação", "óleo/farelo", "ração animal", "portos", "crédito rural"],
    "LEITE": ["laticínios", "varejo alimentar", "cadeia fria", "transporte refrigerado"],
    "GADO_LEITEIRO": ["laticínios", "veterinária", "ração", "mão-de-obra rural"],
    "GADO_BOVINO": ["frigoríficos", "couro", "ração", "transporte animal"],
    "HORTIFRUTI": ["CEASA", "varejo alimentar", "restaurantes", "perdas pós-colheita", "cadeia fria"],
    "TOMATE": ["CEASA", "molhos/processados", "varejo", "food service"],
    "BATATA": ["varejo", "food service", "indústria de congelados", "CEASA"],
    "CEBOLA": ["varejo", "CEASA", "restaurantes", "armazenagem"],
    "MANGA": ["exportação", "fruticultura", "embalagens", "cadeia fria"],
}

REGION_RULES = {
    "RJ": {
        "region": "Rio de Janeiro",
        "main_channels": ["CEASA-RJ", "Região Metropolitana do Rio", "Norte Fluminense", "Médio Paraíba", "portos e rodovias BR-101/BR-116"],
        "national_effect": "baixo a médio, geralmente concentrado em abastecimento regional e perecíveis; impacto nacional aumenta quando envolve leite, milho/ração, portos, crédito ou fornecedor de rede varejista nacional."
    },
    "SP": {"region": "São Paulo", "main_channels": ["CEAGESP", "indústria alimentar", "varejo nacional", "logística Sudeste"], "national_effect": "alto pela centralidade de consumo, distribuição e formação de preços."},
    "MG": {"region": "Minas Gerais", "main_channels": ["café", "leite", "hortifruti", "grãos"], "national_effect": "alto em café e leite; médio em hortifruti regional."},
    "PR": {"region": "Paraná", "main_channels": ["grãos", "proteína animal", "cooperativas", "Porto de Paranaguá"], "national_effect": "alto em soja, milho, frango, suínos e exportação."},
    "RS": {"region": "Rio Grande do Sul", "main_channels": ["arroz", "trigo", "soja", "proteína animal"], "national_effect": "alto em arroz e trigo; médio/alto em grãos e proteína."},
    "MT": {"region": "Mato Grosso", "main_channels": ["soja", "milho", "algodão", "exportação"], "national_effect": "muito alto em grãos e comércio exterior."},
    "GO": {"region": "Goiás", "main_channels": ["grãos", "tomate industrial", "leite", "carnes"], "national_effect": "alto em grãos, tomate industrial e proteínas."},
    "BA": {"region": "Bahia", "main_channels": ["frutas", "grãos MATOPIBA", "cacau"], "national_effect": "alto em frutas exportáveis, cacau e grãos do Oeste baiano."},
    "PE": {"region": "Pernambuco", "main_channels": ["fruticultura irrigada", "CEASA", "porto/aeroporto"], "national_effect": "médio/alto em frutas frescas e exportação do Vale do São Francisco."},
}


def _db_path() -> str:
    for p in DB_PATHS:
        if os.path.exists(p):
            return p
    return DB_PATHS[0]


def _parse_json(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def _normalize_product(p: str) -> str:
    return str(p or "").strip().upper().replace(" ", "_").replace("Ç", "C").replace("Ã", "A").replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U")


def _sectors_for_products(products: List[str]) -> List[str]:
    sectors = []
    for p in products:
        key = _normalize_product(p)
        sectors.extend(SECTOR_RULES.get(key, []))
        if not SECTOR_RULES.get(key) and any(x in key for x in ["ALFACE", "BANANA", "FRUTA", "HORT", "VERDURA"]):
            sectors.extend(SECTOR_RULES["HORTIFRUTI"])
    seen = []
    for s in sectors:
        if s not in seen:
            seen.append(s)
    return seen[:10]


def _risk_score(row: sqlite3.Row) -> Tuple[int, List[str]]:
    score = 25
    reasons = []
    status = (row["judicial_status"] or "").lower()
    debt = float(row["debts_total"] or 0)
    revenue = float(row["annual_revenue"] or 0)
    employees = int(row["employees"] or 0)
    products = _parse_json(row["products"], [])

    if "fal" in status:
        score += 35; reasons.append("status judicial indica falência/risco terminal")
    elif "recuper" in status:
        score += 25; reasons.append("empresa em recuperação judicial exige monitoramento de continuidade")
    if revenue > 0 and debt / revenue >= 1.5:
        score += 20; reasons.append("dívida informada supera 150% da receita anual")
    elif revenue > 0 and debt / revenue >= 0.8:
        score += 12; reasons.append("alavancagem relevante frente à receita anual")
    if employees >= 100:
        score += 10; reasons.append("potencial impacto relevante sobre emprego local")
    if any(_normalize_product(p) in ["LEITE", "GADO_LEITEIRO", "TOMATE", "BATATA", "CEBOLA", "HORTIFRUTI"] for p in products):
        score += 8; reasons.append("produto perecível/cadeia fria eleva risco de ruptura regional")
    return min(score, 100), reasons[:5]


def _impact_level(score: int) -> str:
    if score >= 75: return "alto"
    if score >= 55: return "médio-alto"
    if score >= 35: return "médio"
    return "baixo"


def load_rj_cases(limit: int = 100, uf: str | None = None) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    q = "SELECT * FROM flv_producers_rj WHERE 1=1"
    args: List[Any] = []
    if uf:
        q += " AND state_uf=?"
        args.append(uf.upper())
    q += " ORDER BY COALESCE(last_judicial_update, updated_at, entry_date, created_at) DESC LIMIT ?"
    args.append(limit)
    rows = cur.execute(q, args).fetchall()
    conn.close()

    cases = []
    for r in rows:
        products = _parse_json(r["products"], [])
        volume = _parse_json(r["production_volume"], {})
        score, reasons = _risk_score(r)
        uf_code = (r["state_uf"] or "RJ").upper()
        region_info = REGION_RULES.get(uf_code, REGION_RULES["RJ"])
        sectors = _sectors_for_products(products)
        cases.append({
            "company_name": r["company_name"],
            "cnpj": r["cnpj"],
            "process_number": r["process_number"],
            "court": r["court"],
            "judicial_status": r["judicial_status"],
            "city": r["city"],
            "state_uf": uf_code,
            "lat": r["lat"],
            "lon": r["lon"],
            "products": products,
            "production_volume": volume,
            "annual_revenue": r["annual_revenue"],
            "employees": r["employees"],
            "debts_total": r["debts_total"],
            "entry_date": r["entry_date"],
            "last_judicial_update": r["last_judicial_update"] or r["updated_at"],
            "risk_score": score,
            "impact_level": _impact_level(score),
            "impact_reasons": reasons,
            "affected_sectors": sectors,
            "regional_channels": region_info["main_channels"],
            "brazil_impact": region_info["national_effect"],
            "data_confidence": "média: base interna; confirmar processo e movimentações no CNJ/DataJud antes de decisão operacional",
            "validation_source": "CNJ DataJud / tribunal competente / base interna do app"
        })
    return cases


def aggregate(cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    sectors: Dict[str, int] = {}
    by_uf: Dict[str, int] = {}
    products: Dict[str, int] = {}
    total_debts = 0.0
    total_revenue = 0.0
    jobs = 0
    for c in cases:
        by_uf[c["state_uf"]] = by_uf.get(c["state_uf"], 0) + 1
        total_debts += float(c.get("debts_total") or 0)
        total_revenue += float(c.get("annual_revenue") or 0)
        jobs += int(c.get("employees") or 0)
        for s in c.get("affected_sectors", []): sectors[s] = sectors.get(s, 0) + 1
        for p in c.get("products", []): products[p] = products.get(p, 0) + 1
    return {
        "rj_cases": len(cases),
        "states_covered": len(by_uf),
        "total_debts_brl": round(total_debts, 2),
        "total_revenue_brl": round(total_revenue, 2),
        "jobs_exposed": jobs,
        "top_sectors": sorted([{"sector": k, "cases": v} for k, v in sectors.items()], key=lambda x: x["cases"], reverse=True)[:12],
        "top_products": sorted([{"product": k, "cases": v} for k, v in products.items()], key=lambda x: x["cases"], reverse=True)[:12],
        "by_uf": sorted([{"uf": k, "cases": v, "region": REGION_RULES.get(k, {}).get("region", k)} for k, v in by_uf.items()], key=lambda x: x["cases"], reverse=True),
    }


def build_payload(params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    params = params or {}
    uf = params.get("uf") or params.get("state")
    if isinstance(uf, list): uf = uf[0]
    try:
        limit = int((params.get("limit") or [100])[0] if isinstance(params.get("limit"), list) else params.get("limit", 100))
    except Exception:
        limit = 100
    cases = load_rj_cases(limit=limit, uf=uf)
    return {
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "panel": "Situation Real",
        "definition": {
            "RJ": "Recuperação Judicial; não confundir com a unidade federativa Rio de Janeiro quando usado como status jurídico.",
            "truth_policy": "O painel não cria dado financeiro, judicial ou climático falso. Quando a conexão oficial não está disponível, mostra base interna e exige validação na fonte oficial."
        },
        "summary": aggregate(cases),
        "cases": cases,
        "sources": OFFICIAL_SOURCES,
        "recommended_live_integrations": [
            "Configurar DATAJUD_API_KEY para validação automática por tribunal/processo.",
            "Conectar IBGE/SIDRA para produção municipal anual e LSPA para estimativas mensais.",
            "Conectar CONAB/PROHORT ou arquivos oficiais com data de referência para abastecimento/preços.",
            "Usar CEPEA/HF Brasil apenas com séries identificadas por produto, região e data."
        ],
        "limitations": [
            "Empresas listadas vêm da base interna do app; o status precisa ser validado no CNJ/DataJud antes de uso jurídico ou financeiro.",
            "Impacto setorial é uma classificação técnica derivada de produtos, localidade, empregados, dívida e receita disponíveis.",
            "Sem chave DataJud não há confirmação automática de movimentação processual em tempo real."
        ]
    }


if __name__ == "__main__":
    print(json.dumps(build_payload({}), ensure_ascii=False, indent=2))
