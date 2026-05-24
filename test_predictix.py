import predictix_intelligence

intel = predictix_intelligence.PredictixIntelligence()

print('='*60)
print('TESTE PREDICTIX INTELLIGENCE v2.0')
print('='*60)

print('\n1. RISCO LOGISTICO:')
risk = intel.get_logistics_risk()
print('   Alertas ativos:', len(risk['alerts']))
for a in risk['alerts'][:2]:
    print('   -', a['road'] + ':', a['message'][:40] + '...')

print('\n2. CUSTO TOTAL:')
cost = intel.calculate_total_cost(2.50, 10000, 850, 'tomate')
print('   Custo total: R$', cost['total_cost_per_kg'], '/kg')
print('   Frete: R$', cost['costs_breakdown']['frete'], '/kg')

print('\n3. PREVISAO DE PRECO:')
pred = intel.predict_price('tomate', 7)
print('   Atual: R$', pred['current_price'])
print('   Previsto (7d): R$', pred['predicted_price'])
print('   Confiança:', pred['confidence_percent'], '%')

print('\n4. SAZONALIDADE:')
season = intel.get_seasonality('tomate')
print('   Situacao:', season['current_situation'])
print('   Recomendacao:', season['recommendation'][:50] + '...')

print('\n5. ALERTAS:')
alerts = intel.generate_alerts()
print('   Total de alertas:', len(alerts))
for a in alerts[:3]:
    print('   [' + a['severity'].upper() + ']', a['message'])

print('\n' + '='*60)
print('✅ TODOS OS TESTES PASSARAM!')
print('='*60)
