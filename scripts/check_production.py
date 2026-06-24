import http.client
import ssl

# Verifica o site em producao
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

conn = http.client.HTTPSConnection('nias.onrender.com', context=ctx)
conn.request('GET', '/')
resp = conn.getresponse()
html = resp.read().decode('utf-8', errors='ignore')
conn.close()

# Procura o botao SITUATION
if "showPanel('situation')" in html or 'showPanel("situation")' in html:
    print("✅ Botao SITUATION encontrado no HTML")
else:
    print("❌ Botao SITUATION NAO encontrado")

# Procura o painel
if 'id="panel-situation"' in html:
    print("✅ Painel panel-situation existe")
    # Verifica se tem conteudo
    start = html.find('id="panel-situation"')
    end = html.find('id="panel-chat"', start)
    panel = html[start:end]
    print(f"Tamanho do painel: {len(panel)} caracteres")
    if len(panel) > 1000:
        print("✅ Painel tem conteudo substancial")
    else:
        print("❌ Painel parece vazio ou truncado")
else:
    print("❌ Painel panel-situation NAO existe")

# Verifica se o JavaScript do SituationRoom existe
if 'const SituationRoom' in html:
    print("✅ JavaScript SituationRoom encontrado")
else:
    print("❌ JavaScript SituationRoom NAO encontrado")
