# Atualização Bio-Command — Polos Hortifrutigranjeiros da América do Sul

Data da atualização: 2026-05-24

## Escopo implementado

Foi adicionada uma base curada de polos produtivos hortifrutigranjeiros da América do Sul no Bio-Command, cobrindo frutas, hortaliças, tubérculos, flores, arroz, ovos, aves, leite e cadeias de granja/região.

## Alterações principais

- `index.html`
  - Nova base `MUNICIPAL_DB_SOUTH_AMERICA_HF` com 53 polos produtivos sul-americanos.
  - Inclusão automática no `MUNICIPAL_DB` usado pelo mapa Bio-Command.
  - Novo indicador no topo do Bio-Command: quantidade de polos e países cobertos.
  - Novos filtros de culturas/produtos: cacau, mandioca, aspargos, palta/avocado, arándano/mirtilo, brócolis, mandarina, ovos, frango e leite.

- `flv/south_america_hf_poles.json`
  - Base estruturada em JSON para reuso backend.

- `flv/seed_south_america_hf_poles.py`
  - Script de carga dos polos no banco SQLite `nia_flv.db`, tabela `flv_producers`.
  - Inseridos 53 novos registros no banco local durante esta atualização.

## Países cobertos

Argentina, Bolívia, Chile, Colômbia, Equador, Guiana, Guiana Francesa, Paraguai, Peru, Suriname, Uruguai e Venezuela. O Brasil já possuía base ampla no projeto e permanece integrado ao mesmo mapa.

## Observação de precisão

A cobertura adicionada é em nível de polo/município-região, adequada para visualização estratégica, filtros e análise de risco do Bio-Command. Não é um cadastro exaustivo de propriedades rurais. Volumes são ordens de grandeza operacionais para painel e não devem ser tratados como estatística oficial final sem integração com fontes nacionais por país.

## Validação executada

- `node test_syntax.js`: sintaxe OK.
- Execução do seed `flv/seed_south_america_hf_poles.py`: 53 polos inseridos.
