import http.client

conn = http.client.HTTPConnection('localhost', 8080, timeout=5)
conn.request('GET', '/')
resp = conn.getresponse()
html = resp.read().decode('utf-8', errors='ignore')
conn.close()

# Verifica se os elementos essenciais existem
checks = [
    ('Botao SITUATION', "showPanel('situation')"),
    ('Painel situation', 'id="panel-situation"'),
    ('Painel chat', 'id="panel-chat"'),
    ('initChatIA', 'function initChatIA'),
    ('SituationRoom', 'const SituationRoom'),
]

print('=== VERIFICACAO DO SISTEMA ===\n')
for name, pattern in checks:
    if pattern in html:
        print(f'✅ {name}: OK')
    else:
        print(f'❌ {name}: FALTANDO')

# Verifica se o painel situation tem conteudo
start = html.find('id="panel-situation"')
if start != -1:
    end = html.find('id="panel-chat"', start)
    panel = html[start:end]
    print(f'\nTamanho do painel situation: {len(panel)} caracteres')
    if len(panel) > 5000:
        print('✅ Painel tem conteudo completo')
    else:
        print('⚠️ Painel pode estar incompleto')
