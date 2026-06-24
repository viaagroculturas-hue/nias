# Relatório — Atualização da Aba Mercado

Data: 2026-05-24

## Objetivo
Organizar a aba Mercado para evitar dados simulados, arbitragem fictícia e indicadores sem fonte verificável.

## Alterações aplicadas

1. Substituição do painel antigo de "Terminal de Arbitragem / Alta Frequência" por painel "Mercado — Dados Reais Curados".
2. Remoção visual de indicadores não auditáveis, como:
   - ciclo de 3,5s;
   - IC 94%;
   - melhor spread automático;
   - oportunidades HFT;
   - frete médio IA sem fonte.
3. Inclusão de tabela estruturada com:
   - produto;
   - categoria;
   - produção/oferta;
   - preço somente quando houver fonte conectada;
   - tendência qualitativa;
   - região/terminal;
   - fonte;
   - status do dado.
4. Separação explícita entre:
   - produção/oferta anual;
   - preço spot;
   - pendência de fonte.
5. Inclusão de filtros por categoria, fonte e busca livre.
6. Inclusão de exportação CSV.
7. Inclusão de base JSON em `flv/market_real_data.json`.

## Critério adotado
O painel agora não inventa preços. Quando não há cotação diária conectada, o campo é exibido como `—` e a linha mantém apenas produção/oferta ou referência setorial.

## Fontes usadas como referência de curadoria
- CONAB: produção e informação agropecuária.
- IBGE PAM: produção agrícola municipal anual.
- CNA Mapa Hortifruti: volumes de frutas/hortaliças em mil toneladas.
- CEAGESP/CEASAs: referência futura para cotação por terminal e classificação.
- CEPEA: referência futura para séries de preço por produto específico.

## Pendências para dado 100% dinâmico
- Conectar API/rotina oficial CEAGESP/CEASAs por produto, variedade, embalagem e classificação.
- Conectar CEPEA para séries de preço agropecuário.
- Conectar CONAB/SISDEP para cotações semanais quando aplicável.
- Implementar rotina de atualização com timestamp e validação de outliers.

## Validação
- `node test_syntax.js`: Sintaxe OK.
