"""FLV SIDRA/IBGE Production Collector — Municipal agricultural production."""
import urllib.request, json

# SIDRA table 1612 = PAM (Producao Agricola Municipal)
# Variable 214 = production (tons), 112 = area harvested (ha)
SIDRA_CULTURES = {
    'tomate': '0133', 'cebola': '0052', 'batata': '0020', 'cenoura': '0040',
    'manga': '0079', 'uva': '0145', 'banana': '0018', 'laranja': '0083',
    'maca': '0075', 'melao': '0080', 'mamao': '0076', 'abacaxi': '0001',
    'alho': '0008', 'morango': '0088',
}

def fetch_all():
    """Fetch production data from SIDRA for all FLV cultures."""
    from flv.db import get_conn
    conn = get_conn()
    inserted = 0

    for slug, prod_code in SIDRA_CULTURES.items():
        try:
            count = _fetch_culture(conn, slug, prod_code)
            inserted += count
        except Exception as e:
            print(f'[FLV-SIDRA] Erro {slug}: {e}')

    conn.commit()
    print(f'[FLV-SIDRA] {inserted} registros de producao inseridos')
    return inserted

def _fetch_culture(conn, slug, prod_code):
    """Fetch SIDRA PAM table 1612 for a specific product."""
    cid = conn.execute("SELECT id FROM flv_cultures WHERE slug=?", (slug,)).fetchone()
    if not cid:
        return 0

    # Table 1612: PAM, variable 214 (production), last period, all municipalities
    url = (f"https://apisidra.ibge.gov.br/values/t/1612/n6/all"
           f"/v/214/p/last/c81/{prod_code}/d/v214%200")
    req = urllib.request.Request(url, headers={'User-Agent': 'NIA$-FLV/1.0'})

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print(f'[FLV-SIDRA] HTTP error for {slug}: {e}')
        return 0

    if not isinstance(data, list) or len(data) < 2:
        return 0

    count = 0
    for row in data[1:]:
        ibge_code = row.get('D1C', '')
        if not ibge_code or len(ibge_code) != 7:
            continue

        # Only insert for municipalities we track
        mid = conn.execute("SELECT id FROM flv_municipalities WHERE ibge_code=?", (ibge_code,)).fetchone()
        if not mid:
            continue

        try:
            production = float(row.get('V', '0') or '0')
        except ValueError:
            continue

        year_str = row.get('D3C', '')
        try:
            year = int(year_str[:4]) if year_str else 2025
        except ValueError:
            year = 2025

        try:
            conn.execute(
                "INSERT OR REPLACE INTO flv_production (mun_id,culture_id,year,production_tons,source) VALUES (?,?,?,?,?)",
                (mid['id'], cid['id'], year, production, 'SIDRA-PAM')
            )
            count += 1
        except Exception:
            pass

    return count
