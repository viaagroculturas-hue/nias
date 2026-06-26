"""
CEAGESP Live Scraper — Cotacoes diarias de hortifruti
Fonte: https://ceagesp.gov.br/cotacoes/
Atualizado a cada cotacao (2-3x por semana, seg/qua/sex)
"""
import json, re, time

_ceagesp_cache = {}
_ceagesp_ttl = 1800  # 30 min cache

# Product name mapping: CEAGESP name fragment -> FLV slug
CEAGESP_MAP = {
    'TOMATE LONGA VIDA': 'tomate', 'TOMATE CARMEM': 'tomate', 'TOMATE ITALIANO': 'tomate', 'TOMATE': 'tomate',
    'CEBOLA NACIONAL': 'cebola', 'CEBOLA ROXA': 'cebola', 'CEBOLA BRANCA': 'cebola', 'CEBOLA': 'cebola',
    'BATATA-DOCE': 'batata-doce', 'BATATA AGATA': 'batata', 'BATATA ASTERIX': 'batata', 'BATATA INGLESA': 'batata', 'BATATA': 'batata',
    'PIMENTAO VERDE': 'pimentao', 'PIMENTAO VERMELHO': 'pimentao', 'PIMENTAO AMARELO': 'pimentao',
    'PIMENTÃO VERDE': 'pimentao', 'PIMENTÃO VERMELHO': 'pimentao', 'PIMENTÃO AMARELO': 'pimentao',
    'CENOURA': 'cenoura',
    'ALFACE CRESPA': 'folhosas', 'ALFACE AMERICANA': 'folhosas', 'ALFACE LISA': 'folhosas',
    'BANANA NANICA': 'banana', 'BANANA PRATA': 'banana', 'BANANA MACA': 'banana', 'BANANA MAÇÃ': 'banana',
    'LARANJA PERA': 'laranja', 'LARANJA LIMA': 'laranja', 'LARANJA NATAL': 'laranja', 'LARANJA': 'laranja',
    'MANGA TOMMY': 'manga', 'MANGA PALMER': 'manga', 'MANGA ESPADA': 'manga', 'MANGA': 'manga',
    'UVA ITALIA': 'uva', 'UVA NIAGARA': 'uva', 'UVA THOMPSON': 'uva', 'UVA RUBI': 'uva',
    'UVA ITÁLIA': 'uva', 'UVA NIÁGARA': 'uva',
    'MAMAO FORMOSA': 'mamao', 'MAMAO PAPAYA': 'mamao', 'MAMÃO FORMOSA': 'mamao', 'MAMÃO PAPAYA': 'mamao',
    'MELANCIA': 'melancia',
    'MELAO AMARELO': 'melao', 'MELAO REI': 'melao', 'MELÃO AMARELO': 'melao', 'MELÃO': 'melao',
    'ABACAXI PEROLA': 'abacaxi', 'ABACAXI HAVAI': 'abacaxi', 'ABACAXI PÉROLA': 'abacaxi', 'ABACAXI': 'abacaxi',
    'MARACUJA': 'maracuja', 'MARACUJÁ': 'maracuja',
    'GOIABA VERMELHA': 'goiaba', 'GOIABA BRANCA': 'goiaba', 'GOIABA': 'goiaba',
    'ABACATE AVOCADO': 'abacate', 'ABACATE FORTUNA': 'abacate', 'ABACATE MARGARIDA': 'abacate', 'ABACATE': 'abacate',
    'LIMAO TAHITI': 'limao', 'LIMAO GALEGO': 'limao', 'LIMÃO TAHITI': 'limao', 'LIMÃO': 'limao',
    'TANGERINA PONKAN': 'tangerina', 'TANGERINA MURCOTT': 'tangerina', 'TANGERINA': 'tangerina',
    'COCO VERDE': 'coco', 'COCO SECO': 'coco', 'COCO': 'coco',
    'MORANGO': 'morango',
    'MACA FUJI': 'maca', 'MACA GALA': 'maca', 'MAÇÃ FUJI': 'maca', 'MAÇÃ GALA': 'maca', 'MAÇÃ': 'maca',
    'ALHO NACIONAL': 'alho', 'ALHO': 'alho',
    'PEPINO': 'pepino',
    'BROCOLIS': 'brocolis', 'BRÓCOLIS': 'brocolis',
    'COUVE FLOR': 'couve-flor', 'COUVE-FLOR': 'couve-flor',
    'REPOLHO': 'repolho',
}

CEAGESP_PREFER = {
    'tomate': 'CARMEM', 'banana': 'NANICA', 'laranja': 'PERA', 'manga': 'PALMER',
    'uva': 'NIAGARA', 'batata': 'AGATA', 'cebola': 'NACIONAL', 'mamao': 'FORMOSA',
    'abacate': 'AVOCADO', 'limao': 'TAHITI', 'pimentao': 'VERDE', 'folhosas': 'CRESPA',
    'maca': 'FUJI', 'alho': 'NACIONAL',
}


def _make_session():
    """Returns a session object — curl_cffi preferred, requests as fallback."""
    try:
        from curl_cffi import requests as cr
        s = cr.Session(impersonate="chrome120")
        s._backend = 'curl_cffi'
        return s
    except ImportError:
        import requests as rq
        s = rq.Session()
        s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        })
        s._backend = 'requests'
        return s


def fetch_ceagesp():
    """Fetch current prices from CEAGESP cotacoes (latest available date)."""
    global _ceagesp_cache
    now = time.time()
    if _ceagesp_cache.get('data') and now - _ceagesp_cache.get('ts', 0) < _ceagesp_ttl:
        return _ceagesp_cache['data']

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[CEAGESP] beautifulsoup4 não instalado")
        return {}

    s = _make_session()
    result = {'products': {}, 'meta': {}}

    try:
        r0 = s.get("https://ceagesp.gov.br/cotacoes/", timeout=20)
        if r0.status_code != 200:
            print(f"[CEAGESP] GET retornou {r0.status_code}")
            return {}

        dates_match = re.search(r'var Grupos = ({.*?});', r0.text, re.DOTALL)
        if not dates_match:
            print("[CEAGESP] var Grupos não encontrado na página")
            return {}

        grupos = json.loads(dates_match.group(1))
        meta_date = None

        for group in ["FRUTAS", "LEGUMES", "VERDURAS"]:
            dates = grupos.get(group, [])
            if not dates:
                continue
            latest = dates[-1]  # mais recente disponível
            if not meta_date:
                meta_date = latest
                result['meta']['date'] = latest
                result['meta']['source'] = 'CEAGESP'
                result['meta']['groups'] = list(grupos.keys())
                result['meta']['updated_at'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

            r = s.post(
                "https://ceagesp.gov.br/cotacoes/",
                data={"cot_grupo": group, "cot_data": latest},
                headers={
                    "Referer": "https://ceagesp.gov.br/cotacoes/",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                timeout=25,
            )
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table")
            if not table:
                continue

            rows = table.find_all("tr")
            parsed = 0
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all("td")]
                if len(cells) < 5:
                    continue

                product_name = cells[0].upper().strip()
                classification = cells[1].strip()
                unit = cells[2].strip()

                try:
                    price_min = float(cells[3].replace(".", "").replace(",", "."))
                    price_avg = float(cells[4].replace(".", "").replace(",", "."))
                    price_max = float(cells[5].replace(".", "").replace(",", ".")) if len(cells) > 5 else price_avg
                except (ValueError, IndexError):
                    continue

                if price_avg <= 0:
                    continue

                # Map to FLV slug — longest match wins
                slug = None
                best_len = 0
                for key, s_slug in CEAGESP_MAP.items():
                    if (product_name.startswith(key) or key in product_name) and len(key) > best_len:
                        slug = s_slug
                        best_len = len(key)

                if not slug:
                    continue

                prefer = CEAGESP_PREFER.get(slug, '')
                is_preferred = bool(prefer and prefer.upper() in product_name)
                existing = result['products'].get(slug)
                if not existing or is_preferred or (not existing.get('_preferred') and classification in ('A', '-', 'PRIMEIRA', '1A', '2A')):
                    result['products'][slug] = {
                        'name': product_name,
                        'classification': classification,
                        'unit': unit,
                        'price_min': price_min,
                        'price_avg': price_avg,
                        'price_max': price_max,
                        'group': group,
                        'date': latest,
                        'source': f'CEAGESP · {latest}',
                        '_preferred': is_preferred,
                    }
                    parsed += 1

            print(f"[CEAGESP] {group} ({latest}): {parsed} produtos mapeados")
            time.sleep(0.4)

        if result['products']:
            _ceagesp_cache['data'] = result
            _ceagesp_cache['ts'] = now
            print(f"[CEAGESP] Total: {len(result['products'])} produtos · Backend: {getattr(s, '_backend', '?')}")

    except Exception as e:
        import traceback
        print(f"[CEAGESP] Erro: {e}")
        traceback.print_exc()

    return result


if __name__ == "__main__":
    data = fetch_ceagesp()
    print(f"\n{'='*60}")
    print(f"CEAGESP — {data.get('meta',{}).get('date','')} — {len(data.get('products',{}))} produtos")
    print(f"Backend: {data.get('meta',{}).get('source','')}")
    print(f"{'='*60}")
    for slug, p in sorted(data.get('products', {}).items()):
        pref = '★' if p.get('_preferred') else ' '
        print(f"  {pref} {slug:14s}: R$ {p['price_avg']:>7.2f}/{p['unit']:4s}  ({p['date']})  {p['name'][:35]}")
