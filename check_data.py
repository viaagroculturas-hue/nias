import sqlite3
conn = sqlite3.connect('nia_flv.db')
cursor = conn.cursor()

# Verifica se ha dados em flv_producers_rj
cursor.execute("SELECT COUNT(*) FROM flv_producers_rj")
count = cursor.fetchone()[0]
print(f'Empresas em flv_producers_rj: {count}')

# Verifica se ha dados em flv_distributors
cursor.execute("SELECT COUNT(*) FROM flv_distributors")
count = cursor.fetchone()[0]
print(f'Distribuidores: {count}')

conn.close()
