import re
with open('nias.html','r',encoding='utf-8') as f:
    c = f.read()
pat = r"id:'(BR-[^']+)'.*?name:'([^']+)'.*?culture:'([^']+)'"
entries = re.findall(pat, c)
print(f'Total BR: {len(entries)} municipios')
cultures = {}
states = {}
for eid, name, cult in entries:
    cultures[cult] = cultures.get(cult, 0) + 1
    st = eid.split('-')[1]
    states[st] = states.get(st, 0) + 1
print('\nPor cultura:')
for k, v in sorted(cultures.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}')
print('\nPor estado:')
for k, v in sorted(states.items(), key=lambda x: -x[1]):
    print(f'  {k}: {v}')
