# Correção final — endpoints IA e Dashboard

## Problemas identificados no Render

1. `/api/flv/ia/analyze` retornava:
   - `no such column: is_synthetic`
   - causa: banco SQLite em produção sem colunas novas de qualidade dos dados.

2. `/api/dashboard/summary` retornava 404:
   - causa: método `_serve_dashboard_summary_api` ausente ou versão antiga do `server.py` em produção.

## Correções aplicadas

- Criado `flv/db_migration.py`.
- `flv/db.py` agora aplica migração automática e segura ao abrir o banco.
- `flv/dashboard_summary_api.py` agora respeita `NIAS_DB_PATH`.
- `server.py` agora contém o handler explícito de `/api/dashboard/summary`.
- APIs foram testadas localmente com `NIAS_DB_PATH=data/nia_flv.db`.

## Endpoints validados

- `/api/flv/ia/analyze` → HTTP 200
- `/api/dashboard/summary` → HTTP 200

## Variável obrigatória no Render

```env
NIAS_DB_PATH=/opt/render/project/src/data/nia_flv.db
```

## Observação

Depois de subir este pacote no GitHub, faça `Manual Deploy → Clear build cache & deploy` no Render para garantir que a versão antiga não permaneça em cache.
