# Extrai o codigo JavaScript do SituationRoom do index.html e verifica sintaxe

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Procura o codigo do SituationRoom
start = html.find('const SituationRoom = {')
if start == -1:
    print("SituationRoom nao encontrado")
else:
    # Pega ate o proximo '};' seguido de linha em branco ou comentario
    end_marker = '\n};\n'
    end = html.find(end_marker, start)
    if end == -1:
        end = html.find('\n};\n//', start)
    if end == -1:
        end = len(html)
    else:
        end += len(end_marker)
    
    code = html[start:end]
    print(f"Codigo encontrado: {len(code)} caracteres")
    print("\nPrimeiras 500 chars:")
    print(code[:500])
    print("\n\nUltimas 500 chars:")
    print(code[-500:])
