# Correção — Botões AUDITAR SISTEMA e ANALISAR AGORA

## Problema encontrado

Os endpoints do painel inicial retornavam erro porque o backend estava abrindo bancos SQLite vazios deixados na raiz do projeto e dentro de `/flv`, em vez do banco populado em `data/nia_flv.db`.

Endpoints afetados:

- `/api/flv/ia/analyze`
- `/api/system/audit`
- `/api/system/sources`

## Correção aplicada

1. `flv/db.py`
   - agora prioriza `NIAS_DB_PATH` quando definido;
   - depois usa `data/nia_flv.db`;
   - ignora bancos vazios/placeholder menores que 8 KB;
   - mantém fallback seguro para compatibilidade.

2. `flv/system_audit_api.py`
   - agora também busca o banco correto em `data/nia_flv.db`;
   - ignora bancos vazios.

## Validação executada

- `/api/flv/ia/analyze` → HTTP 200
- `/api/system/audit` → HTTP 200
- `python3 -m py_compile` → OK

## Recomendação para Render

Opcional, mas recomendado:

```env
NIAS_DB_PATH=/opt/render/project/src/data/nia_flv.db
```

Isso força o backend a usar o banco correto em produção.
