# Relatório — API CEASA/PROHORT de preços oficiais

## Objetivo
Criar uma API no NIAS para coletar preços de hortifrutigranjeiros por CEASA/UF sem fabricar valores.

## Endpoints adicionados

- `GET /api/ceasa/prices`
- `GET /api/ceasa/precos`

### Parâmetros

- `uf=SP` filtra por estado.
- `product=tomate` ou `produto=tomate` filtra por produto.
- `ceasa=contagem` filtra por entreposto.
- `limit=300` limita registros.
- `refresh=1` força nova coleta, ignorando cache.

## Fontes configuradas

1. CONAB/PROHORT — Mercado Atacadista Hortigranjeiro.
2. CONAB/PROHORT — Preços Diários via Pentaho público.
3. CEAGESP Cotações — referência estadual São Paulo.
4. Base local CEASA do NIAS — usada como cache/fallback, marcada como `local_cache_verify_source`.

## Regra de verdade

O sistema só mostra preço quando a coleta retorna valor de fonte oficial/referencial ou cache local identificado. Estados sem retorno são marcados como `sem_dado_oficial_disponivel_no_coletor`. Não há geração aleatória, média inventada ou preenchimento artificial por UF.

## Arquivos alterados

- `server.py`
- `flv/ceasa_prices_api.py`
- `index.html`
- `docs/RELATORIO_API_CEASA_PRECOS_OFICIAIS.md`

## Integração visual

A aba Mercado recebeu bloco **CEASA/PROHORT OFICIAL**, com filtros por UF e produto, cobertura por estado e tabela de preços com fonte, data e qualidade.

## Observação operacional

Para cobrir 100% dos estados diariamente, o NIAS deve receber conectores estaduais específicos quando a UF não estiver retornando via PROHORT. A API já explicita a ausência em vez de estimar preço.
