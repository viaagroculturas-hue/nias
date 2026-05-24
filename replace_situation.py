import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

with open('situationroom_fix.js', 'r', encoding='utf-8') as f:
    new_code = f.read()

# Procura o codigo antigo do SituationRoom
pattern = r'const SituationRoom = \{.*?\n\};'

if re.search(pattern, content, re.DOTALL):
    # Substitui
    new_content = re.sub(pattern, new_code.strip(), content, flags=re.DOTALL)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print('✅ Codigo do SituationRoom substituido com sucesso!')
else:
    print('❌ Padrao nao encontrado no index.html')
    print('Tentando encontrar o inicio do codigo...')
    
    # Procura apenas o inicio
    start = content.find('const SituationRoom = {')
    if start != -1:
        print(f'Inicio encontrado na posicao {start}')
        # Pega um trecho
        snippet = content[start:start+500]
        print('Primeiros 500 caracteres:')
        print(snippet)
    else:
        print('SituationRoom nao encontrado no arquivo!')
