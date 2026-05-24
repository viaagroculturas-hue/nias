# Analisador de Informações — Aba IA

## Implementado

- Novo módulo backend: `flv/ai_analyzer.py`.
- Novo endpoint: `/api/flv/ia/analyze`.
- Novo bloco visual no topo da aba `IA` com:
  - registros analisados;
  - percentual de dados sintéticos/proxy;
  - frescor dos dados;
  - alertas vigentes;
  - confiabilidade operacional estimada;
  - achados críticos/atenção;
  - recomendações operacionais.
- Botão `ANALISAR AGORA` na aba IA.
- Atalho lateral: `Executar analisador de informações`.

## Critérios analisados

- Qualidade e origem dos dados (`is_synthetic`, `data_quality`, `source`).
- Frescor por data mais recente em tabelas críticas.
- Movimentos de preço por cultura.
- Alertas vigentes e severidade.
- NDVI sintético/proxy.
- Indicadores macroeconômicos ausentes ou fora de faixa.
- Previsões com `target_date` anterior a `generated_at`.

## Resultado local de validação

O analisador executou com sucesso via Python e retornou payload válido.
Exemplo obtido no banco atual:

- Registros analisados: 11.984
- Sintéticos/proxy: 32,8%
- Frescor mínimo: D-27
- Confiabilidade IA: 51%
- Achados críticos: 1
- Pontos de atenção: 2

