import urllib.request, json, time

urls = {
    'ProhortDiario': 'https://portaldeinformacoes.conab.gov.br/downloads/arquivos/ProhortDiario.txt',
    'PrecosSemanalUF': 'https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosSemanalUF.txt',
    'PrecosSemanalMun': 'https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosSemanalMunicipio.txt',
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

for name, url in urls.items():
    print(f'\n=== {name} ===')
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            text = data.decode('latin-1', errors='ignore')
            lines = text.strip().split('\n')
            print(f'  Size: {len(data)} bytes, Lines: {len(lines)}')
            print(f'  Header: {lines[0][:200]}')
            if len(lines) > 1:
                print(f'  Row 1: {lines[1][:200]}')
            if len(lines) > 2:
                print(f'  Row 2: {lines[2][:200]}')
            print(f'  Last:  {lines[-1][:200]}')
    except Exception as e:
        print(f'  ERROR: {type(e).__name__}: {e}')
