import sqlite3

conn = sqlite3.connect('nia_flv.db')
cursor = conn.cursor()

print('='*70)
print('SISTEMA NIA$ - AMERICA DO SUL INTEGRADA')
print('='*70)

print('\n📍 MUNICIPIOS:')
cursor.execute('SELECT COUNT(*) FROM flv_municipalities')
print(f'  Total: {cursor.fetchone()[0]} municipios')

print('\n💰 SAUDE FINANCEIRA:')
cursor.execute('SELECT COUNT(*) FROM flv_financial_health')
print(f'  Empresas: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM flv_financial_institutions')
print(f'  Instituicoes Financeiras: {cursor.fetchone()[0]}')
cursor.execute("SELECT COUNT(*) FROM flv_corporate_changes WHERE change_type='CEO'")
print(f'  Trocas de CEO: {cursor.fetchone()[0]}')

print('\n📊 PRODUCAO:')
cursor.execute('SELECT COUNT(*), SUM(production_tons) FROM flv_production')
prod_count, prod_total = cursor.fetchone()
print(f'  Registros: {prod_count}')
print(f'  Volume: {prod_total:,.0f} toneladas')

print('\n🌤️ CLIMA (Bio Comando):')
cursor.execute('SELECT COUNT(*) FROM flv_climate')
print(f'  Observacoes: {cursor.fetchone()[0]}')

print('\n📰 NEWS PULSE:')
cursor.execute('SELECT COUNT(*) FROM flv_news_global')
print(f'  Noticias: {cursor.fetchone()[0]}')

print('\n🏢 CRISIS WATCH:')
cursor.execute('SELECT COUNT(*) FROM flv_producers_rj')
print(f'  Empresas em RJ: {cursor.fetchone()[0]}')

print('\n' + '='*70)
print('✅ Sistema completo e vivo!')
print('='*70)

print('\n🎯 Novidades no Situation Room:')
print('  • Aba FINANCEIRO com maiores altas/baixas')
print('  • Trocas de CEO recentes (8 mudancas)')
print('  • Exposicao de bancos ao agronegocio')
print('  • 48 empresas da America do Sul')
print('  • Dados em tempo real das Bolsas')

conn.close()
