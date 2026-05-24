# Relatório — PredictX Live

## Objetivo
Reestruturar a aba **PredictX** para deixar de ser um mapa estático/sem contexto e virar um painel operacional de inteligência para eventos, clima, logística, safra e demanda.

## O que foi alterado

### 1. Nova API
Criado o módulo:

- `flv/predictx_live_api.py`

Endpoints inseridos em `server.py`:

- `/api/predictx/live`
- `/api/predictx/events`

A API retorna:

- evento global monitorado
- ranking de cidades impactadas
- fontes oficiais/multilaterais
- sinais de clima, logística, fertilizantes, ENSO e eventos extremos
- regiões produtivas com tentativa de consulta em tempo real à NASA POWER

### 2. Nova interface PredictX
A aba **PredictX** foi substituída por uma interface futurista:

- KPIs vivos
- mapa com marcadores luminosos
- ranking de cidades afetadas
- explicação causal do impacto da Copa do Mundo 2026
- painel de sinais globais e regionais
- botão `ATUALIZAR AGORA`

### 3. Exemplo implementado: Copa do Mundo 2026
O painel mostra como a Copa pode alterar:

- demanda local por hortifruti e food service
- frete refrigerado
- entregas urbanas
- mão-de-obra temporária
- preço local em cidades-sede

A lógica usa dados oficiais/curados sobre cidades-sede e calendário, não simulação aleatória.

## Fontes seguras configuradas

- FIFA — cidades-sede e calendário oficial
- NOAA CPC / IRI — ENSO, El Niño, La Niña
- NASA POWER — clima por coordenada
- FAO GIEWS — risco agrícola e alimentar
- USGS FEWS NET — risco climático/safra
- ReliefWeb — conflitos, enchentes, greves e emergências
- World Bank Commodities — fertilizantes, energia e commodities

## Observação técnica
Quando a aplicação estiver sem internet ou a fonte externa falhar, o endpoint retorna `is_realtime=false` no item afetado. Isso evita apresentar dado estimado como dado real.

## Validação

- `node test_syntax.js` → Sintaxe OK
- `python3 -m py_compile server.py flv/predictx_live_api.py` → OK
