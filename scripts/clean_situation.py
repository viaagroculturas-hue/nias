import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Procura o padrão: fecha do novo SituationRoom seguido de código antigo
# O novo código termina com "};" e depois vem código antigo com "try {"
pattern = r'(};\s*)(    try \{\s*const response = await fetch\(`/api/dossier/changes)'

def replace_func(match):
    return match.group(1) + '\n\n// ═══════════════════════════════════════════════════════════════════\n// CHAT IA MODULE\n// ═══════════════════════════════════════════════════════════════════\n'

# Aplica a substituição
new_content = re.sub(pattern, replace_func, content, flags=re.DOTALL)

# Remove código antigo do SituationRoom que vem depois
# Procura desde "filterCompanies(type)" antigo até antes do "// ═══ CHAT"
old_code_pattern = r'  filterCompanies\(type\) \{\s*this\.currentFilter = type;[\s\S]*?\}\s*\};\s*'
new_content = re.sub(old_code_pattern, '', new_content)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(new_content)

print('Arquivo limpo com sucesso!')
