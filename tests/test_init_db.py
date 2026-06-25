"""Test: verifica se init_db cria municípios e culturas corretamente."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

test_db = os.path.join('data', 'test_persist_check.db')
if os.path.exists(test_db):
    os.remove(test_db)

os.environ['NIAS_DB_PATH'] = test_db
import importlib
import flv.db
importlib.reload(flv.db)
flv.db.init_db()

conn = flv.db.get_conn()
muns = conn.execute('SELECT COUNT(*) FROM flv_municipalities').fetchone()[0]
cults = conn.execute('SELECT COUNT(*) FROM flv_cultures').fetchone()[0]
print(f'municipalities: {muns}')
print(f'cultures: {cults}')

if muns >= 8:
    print('[PASS] Municipios seed OK')
else:
    print(f'[FAIL] Apenas {muns} municipios')

if cults >= 10:
    print('[PASS] Cultures seed OK')
else:
    print(f'[FAIL] Apenas {cults} cultures')

# Cleanup
try:
    os.remove(test_db)
except:
    pass
