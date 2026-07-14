"""
CEPEA — Centro de Estudos Avançados em Economia Aplicada (ESALQ/USP).
Scraper de cotações públicas: https://www.cepea.esalq.usp.br/br/indicador/
Sem API oficial — parsing de tabela HTML.
"""
import httpx
import logging
import re
from datetime import date
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE = "https://www.cepea.esalq.usp.br/br/indicador"

# slug CEPEA → (nome VIGÍA, unidade, praça)
PRODUTOS = {
    "soja":         ("Soja",         "sc60kg",  "Paranaguá"),
    "milho":        ("Milho",        "sc60kg",  "Campinas"),
    "cafe-arabica": ("Café Arábica", "sc60kg",  "São Paulo"),
    "acucar-vhp":   ("Açúcar VHP",  "t",       "São Paulo"),
    "boi-gordo":    ("Boi Gordo",   "@15kg",   "São Paulo"),
    "suino":        ("Suíno",        "kg",      "Paraná"),
    "frango":       ("Frango",       "kg",      "São Paulo"),
    "algodao":      ("Algodão",      "@15kg",   "São Paulo"),
    "trigo":        ("Trigo",        "t",       "Paraná"),
    "arroz":        ("Arroz",        "sc50kg",  "Rio Grande do Sul"),
    "laranja":      ("Laranja",      "cx40kg",  "São Paulo"),
    "etanol-hidratado": ("Etanol Hidratado", "m3", "São Paulo"),
    "madeira":      ("Madeira",      "m3",      "Paraná"),
    "eucalipto":    ("Eucalipto",    "t",       "São Paulo"),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VIGIA-bot/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}


async def get_cotacao(produto_slug: str) -> dict | None:
    """Extrai a cotação atual de um produto do CEPEA."""
    if produto_slug not in PRODUTOS:
        logger.warning(f"CEPEA: produto desconhecido '{produto_slug}'")
        return None

    nome, unidade, praca = PRODUTOS[produto_slug]
    url = f"{BASE}/{produto_slug}.aspx"

    try:
        async with httpx.AsyncClient(timeout=30, headers=HEADERS, follow_redirects=True) as client:
            r = await client.get(url)
            if r.status_code != 200:
                logger.warning(f"CEPEA {produto_slug} status {r.status_code}")
                return None

        soup = BeautifulSoup(r.text, "html.parser")
        preco, data_ref, variacao = _extrair_cotacao(soup)

        if preco is None:
            logger.warning(f"CEPEA {produto_slug}: não encontrou preço na página")
            return None

        return {
            "produto": nome,
            "slug": produto_slug,
            "preco": preco,
            "unidade": unidade,
            "praca": praca,
            "pais": "BRA",
            "data_cotacao": data_ref or date.today().isoformat(),
            "variacao_pct": variacao,
            "tendencia": "alta" if (variacao or 0) > 0 else "baixa" if (variacao or 0) < 0 else "estavel",
            "fonte": "CEPEA-ESALQ",
            "confianca_pct": 90,
        }

    except Exception as e:
        logger.error(f"CEPEA {produto_slug} erro: {e}")
        return None


async def get_todas_cotacoes() -> list[dict]:
    """Coleta todos os produtos CEPEA em sequência."""
    resultados = []
    for slug in PRODUTOS:
        cotacao = await get_cotacao(slug)
        if cotacao:
            resultados.append(cotacao)
    return resultados


def _extrair_cotacao(soup: BeautifulSoup) -> tuple[float | None, str | None, float | None]:
    """Extrai preço, data e variação da página CEPEA."""
    preco = None
    data_ref = None
    variacao = None

    # CEPEA usa tabela com id "imagenet-indicador1"
    tabela = soup.find("table", {"id": re.compile(r"imagenet-indicador", re.I)})
    if tabela is None:
        tabela = soup.find("table", class_=re.compile(r"indicador", re.I))

    if tabela:
        linhas = tabela.find_all("tr")
        for linha in linhas[1:3]:   # pula cabeçalho
            colunas = linha.find_all("td")
            if len(colunas) >= 2:
                data_txt = colunas[0].get_text(strip=True)
                preco_txt = colunas[1].get_text(strip=True)
                preco = _parse_preco(preco_txt)
                data_ref = _parse_data(data_txt)
                if len(colunas) >= 4:
                    var_txt = colunas[3].get_text(strip=True)
                    variacao = _parse_variacao(var_txt)
                break

    # Fallback: procurar na página por padrão de preço R$
    if preco is None:
        matches = re.findall(r"R\$\s*([\d.,]+)", soup.get_text())
        if matches:
            preco = _parse_preco(matches[0])

    return preco, data_ref, variacao


def _parse_preco(txt: str) -> float | None:
    if not txt:
        return None
    txt = txt.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        v = float(txt)
        return v if v > 0 else None
    except ValueError:
        return None


def _parse_data(txt: str) -> str | None:
    # formatos: "28/06/2026" ou "jun/26"
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", txt)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return None


def _parse_variacao(txt: str) -> float | None:
    txt = txt.replace("%", "").replace(",", ".").strip()
    try:
        return float(txt)
    except ValueError:
        return None
