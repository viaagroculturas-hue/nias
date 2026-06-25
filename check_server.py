import http.client
import time
import re

time.sleep(2)
conn = http.client.HTTPConnection('localhost', 8080, timeout=10)
conn.request('GET', '/')
resp = conn.getresponse()
html = resp.read().decode('utf-8', errors='ignore')
conn.close()

# Verifica se o botão está no HTML
if "showPanel('situation')" in html:
    print('Botão SITUATION está no HTML servido')
else:
    print('Botão SITUATION NÃO está no HTML')
    
# Conta quantos botões de navegação existem
buttons = re.findall(r"onclick=\"showPanel\([^)]+\)\"", html)
print(f'Total de botões de navegação: {len(buttons)}')
for b in buttons[-5:]:
    print(f'  - {b}')
