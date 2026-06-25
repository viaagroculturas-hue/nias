import sqlite3

conn = sqlite3.connect('nia_flv.db')
cursor = conn.cursor()

# Verificar estrutura das tabelas relevantes
print("=== TABELA flv_municipalities ===")
cursor.execute("PRAGMA table_info(flv_municipalities)")
for col in cursor.fetchall():
    print(f"  - {col[1]}")

cursor.execute("SELECT COUNT(*) FROM flv_municipalities")
print(f"\nTotal de municípios: {cursor.fetchone()[0]}")

print("\n=== Exemplo de município ===")
cursor.execute("SELECT * FROM flv_municipalities LIMIT 1")
row = cursor.fetchone()
if row:
    for i, desc in enumerate(cursor.description):
        print(f"  {desc[0]}: {row[i]}")

print("\n=== TABELA flv_cultures ===")
cursor.execute("PRAGMA table_info(flv_cultures)")
for col in cursor.fetchall():
    print(f"  - {col[1]}")

cursor.execute("SELECT COUNT(*) FROM flv_cultures")
print(f"\nTotal de culturas: {cursor.fetchone()[0]}")

print("\n=== TABELA flv_production ===")
cursor.execute("PRAGMA table_info(flv_production)")
for col in cursor.fetchall()[:10]:  # Primeiras 10 colunas
    print(f"  - {col[1]}")

conn.close()
