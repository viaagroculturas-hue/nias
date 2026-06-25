import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Le o novo JavaScript
with open('js_panels.js', 'r', encoding='utf-8') as f:
    new_js = f.read()

# Remove o JavaScript antigo do Chat (initChatIA, sendMessage, etc)
# Procura desde function initChatIA ate o proximo bloco comentado
pattern_chat = r'function initChatIA\(\)[\s\S]*?(?=// ═══════════════════════════════════════════════════════════════════\n// HORTIFRUTIS)'

# Remove o JavaScript antigo do SituationRoom
pattern_situation = r'const SituationRoom = \{[\s\S]*?\n\};'

# Substitui o Chat
html = re.sub(pattern_chat, new_js + '\n\n', html)

# Remove o SituationRoom antigo (ja esta incluido no novo)
html = re.sub(pattern_situation, '', html)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('JavaScript substituido com sucesso!')
