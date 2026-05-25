# Relatório — Dashboard Inicial Atualizado

## Objetivo
Atualizar todas as informações do dashboard inicial e eliminar valores fixos/desatualizados no frontend.

## Alterações aplicadas

- Criada/reestruturada a API `GET /api/dashboard/summary`.
- Corrigido o servidor para registrar `_serve_dashboard_summary_api()`.
- Cards principais agora recebem dados via API:
  - produção/culturas;
  - NDVI;
  - umidade/clima;
  - preços CEASA/CONAB;
  - situação/recuperação judicial;
  - macroindicadores com validação de faixa.
- Weather strip agora usa dados da API e não sobrescreve os valores com simulação após o carregamento.
- Alertas do dashboard deixam de ser texto fixo e passam a vir de `flv_alerts`.
- Topbar passa a refletir NDVI, temperatura e status da API.
- Cada informação retorna:
  - fonte;
  - data;
  - qualidade do dado;
  - status observado, sintético/proxy ou indisponível.

## Arquivos alterados

- `flv/dashboard_summary_api.py`
- `server.py`
- `index.html`

## Fontes previstas no catálogo

- CONAB/PROHORT — preços hortigranjeiros e CEASAs.
- IBGE/SIDRA — produção municipal/agropecuária.
- INMET/NASA POWER — clima observado/agroclima.
- SATVeg/NASA — NDVI/vegetação.
- CNJ/DataJud — recuperação judicial, quando `DATAJUD_API_KEY` estiver configurada.
- NOAA CPC/IRI — ENSO/El Niño/La Niña.

## Política anti-dado falso

O dashboard não deve inventar valor quando a fonte falha. Se não houver dado observado, retorna `—`, `unavailable` ou `synthetic_or_proxy` com fonte e data.

## Validação executada

- `python3 -m py_compile server.py flv/dashboard_summary_api.py`
- `node tests/test_syntax.js`
- teste direto de `build_dashboard_summary()`.
