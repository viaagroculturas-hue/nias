import http.client
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = http.client.HTTPSConnection('nias.onrender.com', context=ctx)
conn.request('GET', '/')
resp = conn.getresponse()
html = resp.read().decode('utf-8', errors='ignore')
conn.close()

print("=== VERIFICACAO DO SITE NA WEB ===\n")

# Verifica botao SITUATION
if "showPanel('situation')" in html:
    print("✅ Botao SITUATION encontrado")
else:
    print("❌ Botao SITUATION NAO encontrado")

# Verifica painel
if 'id="panel-situation"' in html:
    print("✅ Painel panel-situation existe")
    # Verifica se tem conteudo
    start = html.find('id="panel-situation"')
    end = html.find('id="panel-chat"', start)
    panel = html[start:end]
    print(f"   Tamanho: {len(panel)} caracteres")
else:
    print("❌ Painel panel-situation NAO existe")

# Verifica initChatIA
if 'function initChatIA()' in html:
    print("✅ Funcao initChatIA encontrada")
else:
    print("❌ Funcao initChatIA NAO encontrada")

# Verifica SituationRoom
if 'const SituationRoom' in html:
    print("✅ JavaScript SituationRoom encontrado")
else:
    print("❌ JavaScript SituationRoom NAO encontrado")

print("\n=== RESUMO ===")
print("Acesse: https://nias.onrender.com")
print("O botao SITUATION deve estar visivel na sidebar")
