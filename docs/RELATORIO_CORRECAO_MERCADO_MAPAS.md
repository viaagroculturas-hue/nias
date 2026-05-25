# Correção Mercado + Mapas

## Problemas identificados

1. A aba Mercado estava vazia porque o `showPanel('oferta')` chamava a função legada `initOferta()`, que inicializava apenas o gráfico antigo e nunca carregava `renderMercadoReal()` nem `/api/ceasa/prices`.
2. A API de preços CEASA buscava somente a tabela local `cotacoes`; o banco principal `data/nia_flv.db` continha `flv_ceasa_prices` com registros CONAB-Semanal não sintéticos, mas eles não eram lidos.
3. Os limites no mapa dependiam de fonte externa `geoBoundaries`; quando a rede/CORS falhava, nada ficava visível.

## Correções aplicadas

- `showPanel('oferta')` agora chama `initMercadoReal()`.
- `/api/ceasa/prices` agora lê também `data/nia_flv.db -> flv_ceasa_prices` filtrando apenas `is_synthetic = 0`.
- A API retorna 177 registros de preço e cobertura das 27 UFs a partir da base local oficial/referencial `CONAB-Semanal`.
- O frontend reconhece `official_local_db` como preço oficial/local validado.
- Mapas agora têm fallback local de contornos de países sul-americanos e UFs brasileiras, carregado imediatamente antes das camadas externas.
- As camadas externas reais continuam sendo tentadas por cima quando disponíveis.

## Política de verdade dos dados

- Preços sintéticos continuam excluídos da API de preço.
- Se a coleta externa falhar, o painel usa somente registros oficiais/referenciais já persistidos no banco.
- Quando nenhuma fonte existir, o sistema deve mostrar `sem dado`, nunca inventar cotação.

## Validação

- `node tests/test_syntax.js`: OK
- `python3 -m py_compile`: OK
- `build_ceasa_price_payload(force_refresh=True)`: OK, 177 registros, 27/27 UFs.
