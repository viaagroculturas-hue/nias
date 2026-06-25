from flv.collectors.crisis_watch import CrisisWatch
cw = CrisisWatch()
result = cw.get_crisis_summary()
print('Resumo obtido:')
print(f"  Empresas em RJ: {result['totals']['in_rj']}")
print(f"  Falencias: {result['totals']['bankrupt']}")
print(f"  Entradas recentes: {len(result['recent_entries'])}")
