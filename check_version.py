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

# Procura o comentario do SITUATION ROOM BUTTON
if "SITUATION ROOM BUTTON v5.0" in html:
    print("✅ Versao mais recente (v5.0) esta no Render")
else:
    print("❌ Versao no Render esta DESATUALIZADA")
    print("O Render nao fez deploy do ultimo commit")
    print("Ultimo commit local: c73f8bd - Fix: Recria painel Situation Room completo")
    print("\nSOLUCAO:")
    print("1. Va em https://dashboard.render.com")
    print("2. Encontre o servico 'nias'")
    print("3. Clique em 'Manual Deploy' -> 'Deploy latest commit'")
    print("4. Aguarde o deploy completar")
