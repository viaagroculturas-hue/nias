with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Procura o painel situation
start = content.find('id="panel-situation"')
if start == -1:
    print('Painel nao encontrado')
else:
    # Pega 500 caracteres depois
    end = content.find('</div>', start) + 6
    panel_content = content[start:end]
    print(f'Painel encontrado. Tamanho: {len(panel_content)} caracteres')
    print(f'Primeiros 200 chars: {panel_content[:200]}')
    print(f'Ultimos 100 chars: {panel_content[-100:]}')
