"""
LEVANTAMENTO COMPLETO FLV — IBGE SIDRA PAM
Tabela 1612 = Lavouras Temporarias (legumes/verduras)
Tabela 1613 = Lavouras Permanentes (frutas)
v/214 = Quantidade produzida (toneladas), p/last = ultimo ano disponivel
"""
import urllib.request, json, time, sys

HEADERS = {'User-Agent': 'NIA$-FLV/1.0'}

# Tabela 1612 (Temporarias) — c81
TEMP_PRODUCTS = {
    '2688': ('Abacaxi', 'fruta'),
    '2690': ('Alho', 'legume'),
    '2694': ('Batata-doce', 'legume'),
    '2695': ('Batata-inglesa', 'legume'),
    '2697': ('Cebola', 'legume'),
    '2700': ('Ervilha', 'legume'),
    '2709': ('Melancia', 'fruta'),
    '2710': ('Melao', 'fruta'),
    '2715': ('Tomate', 'legume'),
}

# Tabela 1613 (Permanentes) — c82
PERM_PRODUCTS = {
    '2717': ('Abacate', 'fruta'),
    '2720': ('Banana', 'fruta'),
    '2724': ('Caqui', 'fruta'),
    '2727': ('Coco-da-baia', 'fruta'),
    '2730': ('Figo', 'fruta'),
    '2731': ('Goiaba', 'fruta'),
    '2733': ('Laranja', 'fruta'),
    '2734': ('Limao', 'fruta'),
    '2735': ('Maca', 'fruta'),
    '2736': ('Mamao', 'fruta'),
    '2737': ('Manga', 'fruta'),
    '2738': ('Maracuja', 'fruta'),
    '2741': ('Pera', 'fruta'),
    '2742': ('Pessego', 'fruta'),
    '2745': ('Tangerina', 'fruta'),
    '2748': ('Uva', 'fruta'),
    '45981': ('Acai', 'fruta'),
    '2905' : ('Acerola', 'fruta'),
}

results = {}
total_muns = set()
errors = []

def fetch(table, classif, code, name, category):
    url = f"https://apisidra.ibge.gov.br/values/t/{table}/n6/all/v/214/p/last/{classif}/{code}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        errors.append(f'{name}: {e}')
        return 0

    if not isinstance(data, list) or len(data) < 2:
        return 0

    muns = []
    for row in data[1:]:
        ibge = row.get('D1C', '')
        nome_mun = row.get('D1N', '')
        valor = row.get('V', '')
        if not ibge or len(ibge) != 7:
            continue
        try:
            tons = float(valor) if valor and valor not in ('', '-', '...', 'X', '0', '..') else 0
        except:
            tons = 0
        if tons <= 0:
            continue
        muns.append({'ibge': ibge, 'nome': nome_mun, 'tons': tons})
        total_muns.add(ibge)

    results[name] = {'muns': muns, 'category': category}
    return len(muns)

print('=== LEVANTAMENTO FLV BRASIL — IBGE SIDRA PAM ===\n')

print('--- LAVOURAS TEMPORARIAS (Tab 1612) ---')
for code, (name, cat) in TEMP_PRODUCTS.items():
    n = fetch(1612, 'c81', code, name, cat)
    total = sum(m['tons'] for m in results.get(name, {}).get('muns', []))
    print(f'  {name:20s}: {n:5d} mun. | {total:>12,.0f} t')
    time.sleep(0.4)

print('\n--- LAVOURAS PERMANENTES (Tab 1613) ---')
for code, (name, cat) in PERM_PRODUCTS.items():
    n = fetch(1613, 'c82', code, name, cat)
    total = sum(m['tons'] for m in results.get(name, {}).get('muns', []))
    print(f'  {name:20s}: {n:5d} mun. | {total:>12,.0f} t')
    time.sleep(0.4)

# UF map
UF_NAMES = {
    '11':'RO','12':'AC','13':'AM','14':'RR','15':'PA','16':'AP','17':'TO',
    '21':'MA','22':'PI','23':'CE','24':'RN','25':'PB','26':'PE','27':'AL','28':'SE','29':'BA',
    '31':'MG','32':'ES','33':'RJ','35':'SP',
    '41':'PR','42':'SC','43':'RS',
    '50':'MS','51':'MT','52':'GO','53':'DF'
}

# Summary
print(f'\n{"="*70}')
print(f'RESUMO FINAL')
print(f'{"="*70}')
print(f'Total de municipios unicos produtores de FLV: {len(total_muns):,}')
products_with_data = {k: v for k, v in results.items() if v['muns']}
print(f'Produtos com dados: {len(products_with_data)} / {len(TEMP_PRODUCTS) + len(PERM_PRODUCTS)}')

print(f'\nRANKING POR MUNICIPIOS PRODUTORES:')
print(f'{"Produto":20s} {"Cat":8s} {"Mun":>7s} {"Producao":>14s}')
print('-' * 55)
for name in sorted(products_with_data, key=lambda x: -len(products_with_data[x]['muns'])):
    info = products_with_data[name]
    total = sum(m['tons'] for m in info['muns'])
    print(f'  {name:20s} {info["category"]:8s} {len(info["muns"]):>5,d}   {total:>12,.0f} t')

# UF distribution
print(f'\nDISTRIBUICAO POR UF:')
uf_data = {}
for name, info in results.items():
    for m in info.get('muns', []):
        uf = UF_NAMES.get(m['ibge'][:2], m['ibge'][:2])
        if uf not in uf_data:
            uf_data[uf] = {'muns': set(), 'tons': 0}
        uf_data[uf]['muns'].add(m['ibge'])
        uf_data[uf]['tons'] += m['tons']

for uf in sorted(uf_data, key=lambda x: -len(uf_data[x]['muns'])):
    d = uf_data[uf]
    print(f'  {uf}: {len(d["muns"]):>5,d} municipios | {d["tons"]:>14,.0f} t')

if errors:
    print(f'\nErros ({len(errors)}):')
    for e in errors[:10]:
        print(f'  {e}')

# Save
output = {
    'total_municipios_unicos': len(total_muns),
    'total_produtos': len(products_with_data),
    'fonte': 'IBGE SIDRA PAM (Tabelas 1612 + 1613)',
    'ano': '2024 (ultimo disponivel)',
    'por_produto': {},
    'por_uf': {}
}
for name in sorted(products_with_data, key=lambda x: -len(products_with_data[x]['muns'])):
    info = products_with_data[name]
    output['por_produto'][name] = {
        'categoria': info['category'],
        'total_municipios': len(info['muns']),
        'producao_total_tons': round(sum(m['tons'] for m in info['muns'])),
        'municipios': sorted(info['muns'], key=lambda x: -x['tons'])
    }
for uf in sorted(uf_data, key=lambda x: -len(uf_data[x]['muns'])):
    d = uf_data[uf]
    output['por_uf'][uf] = {
        'municipios': len(d['muns']),
        'producao_tons': round(d['tons'])
    }

with open('flv_municipios_brasil.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'\nArquivo salvo: flv_municipios_brasil.json')
