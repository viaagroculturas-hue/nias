import sqlite3
conn = sqlite3.connect('nia_flv.db')
cursor = conn.cursor()

# Verificar estrutura da tabela
cursor.execute("PRAGMA table_info(flv_producers_rj)")
columns = cursor.fetchall()
print('Colunas em flv_producers_rj:')
for col in columns:
    print(f'  - {col[1]}')

# Verificar dados
if 'flv_producers_rj' in [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
    cursor.execute("SELECT COUNT(*) FROM flv_producers_rj")
    count = cursor.fetchone()[0]
    print(f'\nTotal de produtores: {count}')
    
    if count > 0:
        cursor.execute("SELECT * FROM flv_producers_rj LIMIT 1")
        row = cursor.fetchone()
        print(f'\nExemplo de produtor: {row}')

conn.close()

