# Correções aplicadas — qualidade, atualização e coleta de dados FLV

## 1. Datas CEASA/CONAB
- Adicionado `flv/data_quality.py` com normalização de datas para `YYYY-MM-DD`.
- Corrigido o coletor `flv/collectors/ceasa.py` para salvar semanas CONAB como data ISO.
- Migrados registros legados em `nia_flv.db`: `9718` datas de preço normalizadas.

## 2. Ordenação cronológica
- Corrigido `flv/api/routes.py` para ordenar preços por data normalizada, não por texto bruto.
- Corrigido `flv/model/feature_builder.py` para montar séries temporais com ordenação robusta.

## 3. Dados sintéticos/proxy
- Adicionadas colunas `is_synthetic` e `data_quality` no schema para tabelas de coleta.
- Marcados registros sintéticos/proxy/reference no banco.
- Renomeadas fontes legadas:
  - `CEAGESP-ref` -> `synthetic:CEAGESP-ref`
  - `UPDATE-2026-04-27` -> `synthetic:UPDATE-2026-04-27`
- Fallback sintético em CEASA e NDVI fica desativado por padrão; só roda com `FLV_ALLOW_SYNTHETIC_FALLBACK=1`.

## 4. NDVI
- Fonte proxy agora é explicitamente `proxy:OpenMeteo-soil-moisture`.
- Fonte sintética agora é explicitamente `synthetic:seasonal-ndvi`.

## 5. Teleconexões
- `upsert_global_climate` não grava mais linhas vazias quando ONI e Atlântico Norte são `NULL`.
- Linhas vazias existentes foram removidas.

## 6. Macroindicadores
- IPCA 12m agora é calculado por capitalização dos últimos 12 valores mensais da série SGS 433.
- Validação adicionada para impedir IPCA e SELIC fora de faixa plausível.
- Registro legado com IPCA fora de faixa foi limpo.

## 7. Migração
- Criado `migrate_data_quality.py` para reaplicar a migração em outros bancos locais.

## Observação operacional
Dados sintéticos não foram apagados automaticamente, porque podem ser úteis para desenvolvimento. Eles agora estão marcados para não serem confundidos com dados oficiais.
