"""
CEAGESP Live Scraper — Cotacoes diarias de hortifruti
Fonte: https://ceagesp.gov.br/cotacoes/
Atualizado a cada cotacao (2-3x por semana)
"""
import json, re, time

_ceagesp_cache = {}
_ceagesp_ttl = 1800  # 30 min cache

# Product name mapping: CEAGESP name fragment -> FLV slug
CEAGESP_MAP = {
    'TOMATE': 'tomate', 'TOMATE CARMEM': 'tomate', 'TOMATE LONGA VIDA': 'tomate', 'TOMATE ITALIANO': 'tomate',
    'CEBOLA NACIONAL': 'cebola', 'CEBOLA ROXA': 'cebola', 'CEBOLA BRANCA': 'cebola',
    'BATATA AGATA': 'batata', 'BATATA ASTERIX': 'batata', 'BATATA INGLESA': 'batata',
    'PIMENTÃO VERDE': 'pimentao', 'PIMENTÃO VERMELHO': 'pimentao', 'PIMENTÃO AMARELO': 'pimentao',
    'CENOURA': 'cenoura',
    'ALFACE CRESPA': 'folhosas', 'ALFACE AMERICANA': 'folhosas', 'ALFACE LISA': 'folhosas',
    'BANANA NANICA': 'banana', 'BANANA PRATA': 'banana', 'BANANA MAÇÃ': 'banana',
    'LARANJA PERA': 'laranja', 'LARANJA LIMA': 'laranja', 'LARANJA NATAL': 'laranja',
    'MANGA TOMMY': 'manga', 'MANGA PALMER': 'manga', 'MANGA ESPADA': 'manga',
    'UVA ITÁLIA': 'uva', 'UVA NIÁGARA': 'uva', 'UVA THOMPSON': 'uva', 'UVA RUBI': 'uva',
    'MAMÃO FORMOSA': 'mamao', 'MAMÃO PAPAYA': 'mamao',
    'MELANCIA': 'melancia',
    'MELÃO AMARELO': 'melao', 'MELÃO REI': 'melao', 'MELÃO PELE DE SAPO': 'melao',
    'ABACAXI PÉROLA': 'abacaxi', 'ABACAXI HAVAÍ': 'abacaxi',
    'MARACUJÁ': 'maracuja',
    'GOIABA VERMELHA': 'goiaba', 'GOIABA BRANCA': 'goiaba',
    'ABACATE': 'abacate',
    'LIMÃO TAHITI': 'limao', 'LIMÃO GALEGO': 'limao', 'LIMÃO SICILIANO': 'limao',
    'TANGERINA PONKAN': 'tangerina', 'TANGERINA MURCOTT': 'tangerina',
    'COCO VERDE': 'coco', 'COCO SECO': 'coco',
    'MORANGO': 'morango',
    'MAÇÃ FUJI': 'maca', 'MAÇÃ GALA': 'maca',
    'ALHO': 'alho',
}

def fetch_ceagesp():
    """Fetch current prices from CEAGESP cotacoes."""
    global _ceagesp_cache
    if _ceagesp_cache.get('data') and time.time() - _ceagesp_cache.get('ts', 0) < _ceagesp_ttl:
        return _ceagesp_cache['data']

    try:
        from curl_cffi import requests as cr
        from bs4 import BeautifulSoup
    except ImportError:
        return {}

    s = cr.Session(impersonate="chrome120")
    result = {'products': {}, 'meta': {}}

    try:
        # Get available dates
        r0 = s.get("https://ceagesp.gov.br/cotacoes/", timeout=15)
        dates_match = re.search(r'var Grupos = ({.*?});', r0.text)
        if not dates_match:
            return {}
        grupos = json.loads(dates_match.group(1))

        for group in ["FRUTAS", "LEGUMES", "VERDURAS"]:
            dates = grupos.get(group, [])
            if not dates:
                continue
            latest = dates[-1]
            result['meta']['date'] = latest
            result['meta']['source'] = 'CEAGESP'

            r = s.post("https://ceagesp.gov.br/cotacoes/", data={
                "cot_grupo": group,
                "cot_data": latest,
            }, headers={
                "Referer": "https://ceagesp.gov.br/cotacoes/",
                "Content-Type": "application/x-www-form-urlencoded",
            }, timeout=20)

            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")
            if not table:
                continue

            rows = table.find_all("tr")
            for row in rows[1:]:  # skip header
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) < 5:
                    continue

                product_name = cells[0].upper().strip()
                classification = cells[1].strip()
                unit = cells[2].strip()

                try:
                    price_min = float(cells[3].replace(",", "."))
                    price_avg = float(cells[4].replace(",", "."))
                    price_max = float(cells[5].replace(",", ".")) if len(cells) > 5 else price_avg
                except (ValueError, IndexError):
                    continue

                if price_avg <= 0:
                    continue

                # Map to FLV slug
                slug = None
                for key, s_slug in CEAGESP_MAP.items():
                    if product_name.startswith(key) or key in product_name:
                        slug = s_slug
                        break

                if not slug:
                    continue

                # Keep best (most common classification) per slug
                if slug not in result['products'] or classification in ('PRIMEIRA', '1A', '2A', 'A', '-'):
                    result['products'][slug] = {
                        'name': product_name,
                        'classification': classification,
                        'unit': unit,
                        'price_min': price_min,
                        'price_avg': price_avg,
                        'price_max': price_max,
                        'group': group,
                        'date': latest,
                        'source': 'CEAGESP',
                    }

            time.sleep(0.5)

        if result['products']:
            _ceagesp_cache['data'] = result
            _ceagesp_cache['ts'] = time.time()
            print(f"[CEAGESP] {len(result['products'])} produtos coletados ({result['meta'].get('date','')})")

    except Exception as e:
        print(f"[CEAGESP] Erro: {e}")

    return result


if __name__ == "__main__":
    data = fetch_ceagesp()
    print(f"\n{'='*60}")
    print(f"CEAGESP — {data.get('meta',{}).get('date','')} — {len(data.get('products',{}))} produtos")
    print(f"{'='*60}")
    for slug, p in sorted(data.get('products', {}).items()):
        print(f"  {slug:12s}: R$ {p['price_avg']:>6.2f}/{p['unit']:4s}  ({p['name'][:30]} {p['classification']})")
