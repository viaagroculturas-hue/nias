# Correção — campos sem resposta no NIAS

## Problemas encontrados

1. `/api/flv/ia/analyze` podia quebrar em bancos antigos com erro `no such column: is_synthetic`.
2. `/api/dashboard/summary` dependia de colunas novas em bancos SQLite já publicados no Render.
3. Alguns campos do frontend ficavam vazios quando a API retornava lista vazia, `null`, `undefined` ou falha temporária.
4. O mapa dependia de CDN externo para divisas reais; quando a rede/CORS falhava, o status não deixava claro que o fallback local estava ativo.

## Correções aplicadas

- Criado `flv/schema_utils.py` com verificações de tabela/coluna antes de montar SQL.
- `flv/ai_analyzer.py` tornou-se tolerante a schemas antigos.
- `flv/dashboard_summary_api.py` não quebra mais quando `is_synthetic` não existe.
- Inserido guarda global de frontend `niasFillEmptyFields()` para impedir campos visualmente vazios.
- Inserido helper `niasRenderApiFailure()` para mensagem explícita em falhas de API.
- Reforçado estilo dos contornos administrativos fallback no mapa.
- Adicionado teste `tests/test_no_blank_fields.py`.

## Endpoints testados localmente

- `/api/flv/ia/analyze` → 200
- `/api/dashboard/summary` → 200
- `/api/system/audit` → 200
- `/api/ceasa/prices` → 200
- `/api/situation/real` → 200
- `/api/predictx/live` → 200
- `/api/rodovias` → 200
- `/api/produtores` → 200
- `/api/produtores-rj` → 200
- `/api/flv/risk/analyze` → 200

## Variável obrigatória no Render

```env
NIAS_DB_PATH=/opt/render/project/src/data/nia_flv.db
```

Após subir este pacote, faça **Manual Deploy → Clear build cache & deploy**.
