with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Verifica se o arquivo esta corrompido
errors = []

# Verifica se o painel chat existe
if 'id="panel-chat"' not in html:
    errors.append('Painel chat nao encontrado')

# Verifica se initChatIA existe  
if 'function initChatIA()' not in html:
    errors.append('Funcao initChatIA nao encontrada')

# Verifica se o painel situation existe
if 'id="panel-situation"' not in html:
    errors.append('Painel situation nao encontrado')

# Verifica se SituationRoom existe
if 'const SituationRoom' not in html:
    errors.append('SituationRoom nao encontrado')

# Verifica tags de fechamento
if html.count('<script>') != html.count('</script>'):
    errors.append('Tags script desbalanceadas')

if html.count('<div') - html.count('</div>') != 0:
    errors.append('Tags div desbalanceadas')

if errors:
    print('ERROS ENCONTRADOS:')
    for e in errors:
        print(f'  - {e}')
else:
    print('Arquivo parece intacto')
    print(f'Total de linhas: {len(html.splitlines())}')
    print(f'Tamanho: {len(html)} caracteres')
