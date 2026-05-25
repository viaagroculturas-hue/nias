# Atualização — Situation Room / Recuperação Judicial

## O que foi alterado

- Criada base curada em `data/situation_room/recovery_judicial_cases.json`.
- Criado cliente oficial `flv/services/datajud_client.py` para CNJ/DataJud.
- Criado motor `flv/situation/recovery_judicial_registry.py`.
- Adicionado endpoint funcional `/api/situation/real` no `server.py`.
- A aba Situation Room passou a ler `/api/situation/real`, não mais apenas `/api/crisis/summary`.
- Incluído script `scripts/seed_situation_room_rj.py` para sincronizar a base curada com SQLite.

## Fontes oficiais/seguras

- CNJ DataJud API Pública: fonte oficial para metadados processuais públicos.
- RI AgroGalaxy: documentos da recuperação judicial da AgroGalaxy.
- EcoAgro / relatórios processuais: documentos públicos sobre Grupo Patense.

## Regra de verdade

O painel não declara lista nacional exaustiva sem `DATAJUD_API_KEY` ativa. Sem a chave, mostra base pública curada e indica limitação. Com a chave configurada no Render, o endpoint passa a consultar DataJud por tribunal.

## Variável necessária no Render

```env
DATAJUD_API_KEY=sua_chave_datajud
```

## Endpoint

```text
/api/situation/real?limit=500&live=1
```

## Observação operacional

A lista “todas as empresas em recuperação judicial” depende de varredura oficial DataJud por tribunal e atualização contínua. O app agora está preparado para isso, sem inventar dados.
