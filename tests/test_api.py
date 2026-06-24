import sys
import traceback
sys.path.insert(0, '.')

try:
    from flv.collectors.crisis_watch import CrisisWatch
    cw = CrisisWatch()
    result = cw.get_crisis_summary()
    print('API funcionou!')
    print(f"Empresas em RJ: {result['totals']['in_rj']}")
except Exception as e:
    print(f'Erro: {e}')
    traceback.print_exc()
