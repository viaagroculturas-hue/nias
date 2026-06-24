# RELATÓRIO — AUDITORIA COMPLETA DE COMANDOS, ABAS, MAPAS E APIs

## Escopo testado
Foram verificados os pontos críticos do NIAS:

- carregamento da página inicial;
- comandos de navegação `showPanel(...)`;
- existência das janelas/abas chamadas pela sidebar;
- endpoints usados pelo dashboard, IA, auditoria, mercado, situation, PredictX e risco;
- containers dos mapas principal, municipal e PredictX;
- camadas de contorno administrativo com fallback local;
- sintaxe JavaScript e Python.

## Erros encontrados e corrigidos

### 1. Endpoints com risco de travamento por coleta externa
Algumas rotas tentavam consultar fontes externas durante o carregamento normal da tela. Em Render isso podia travar o request e deixar abas vazias.

Corrigido em:

- `/api/ceasa/prices`
- `/api/situation/real`
- `/api/predictx/live`
- `/api/flv/risk/analyze`
- `/api/rodovias`

Agora o padrão é carregamento rápido com base local/fallback explícito. Coleta externa só roda quando solicitada com `live=1` ou `refresh=1`.

### 2. Mercado vazio
A API de preços CEASA tentava baixar arquivos grandes da CONAB antes de ler o banco local. Isso podia atrasar ou bloquear a tela.

Correção:

- leitura local de `data/nia_flv.db` primeiro;
- coleta online apenas com `refresh=1`;
- resposta rápida para a aba Mercado.

### 3. Situation Room demorando por DataJud
A rota tentava buscar DataJud por padrão.

Correção:

- `include_live` agora é falso por padrão;
- usar `?live=1` para consulta externa DataJud;
- sem chave/DataJud, a tela mostra base curada e limitação.

### 4. PredictX e API de risco travando por NASA/NOAA/ReliefWeb
As rotas faziam chamadas externas em série.

Correção:

- modo rápido offline por padrão;
- fontes externas ativadas somente com `live=1`;
- payload informa `source_status: offline_fast_mode` quando não houve consulta online.

### 5. Rodovias travando
A rota `/api/rodovias` chamava PRF/DNIT no carregamento padrão.

Correção:

- resposta rápida padrão;
- coleta externa apenas com `/api/rodovias?live=1`.

### 6. APIs antigas sem tabelas
Algumas rotas retornavam HTTP 500 quando tabelas antigas não existiam.

Correção:

- rotas retornam HTTP 200 com status `empty` quando a tabela ainda não existe;
- o painel não quebra por ausência de tabela legada.

### 7. Mapas sem divisas visíveis
As divisas dependiam de fonte externa. Se geoBoundaries/IBGE/CDN falhasse, o mapa podia ficar sem contornos.

Correção validada:

- fallback local de países da América do Sul;
- fallback local das UFs do Brasil;
- contornos no mapa principal;
- contornos no mapa municipal;
- contornos no PredictX.

## Endpoints testados localmente

Todos retornaram HTTP 200 no teste automatizado:

```text
/                                   200
/api/dashboard/summary              200
/api/flv/ia/analyze                 200
/api/system/audit                   200
/api/system/sources                 200
/api/ceasa/prices                   200
/api/situation/real                 200
/api/predictx/live                  200
/api/flv/risk/analyze               200
/api/flv/risk/sources               200
/api/flv/cultures                   200
/api/flv/prices                     200
/api/flv/alerts                     200
/api/flv/heatmap                    200
/api/ceasas                         200
/api/produtores                     200
/api/rodovias                       200
/api/warroom/status                 200
/api/crisis/events                  200
/api/growth/scores                  200
/api/distributors                   200
/api/news                           200
/api/reports                        200
/api/autonomous/status              200
/api/predictix/intel                200
```

## Testes incluídos

Novo arquivo:

```text
tests/test_system_full.py
```

Executar com servidor local:

```bash
NIAS_BASE_URL=http://127.0.0.1:8080 python tests/test_system_full.py
```

## Validação executada

```bash
node tests/test_syntax.js
python3 -m py_compile $(find . -name "*.py")
NIAS_BASE_URL=http://127.0.0.1:8768 python3 tests/test_system_full.py
```

Resultado:

```text
Sintaxe OK
OK: 25 endpoints + estrutura de abas/mapas validados.
```

## Variáveis recomendadas no Render

```env
NIAS_DB_PATH=/opt/render/project/src/data/nia_flv.db
ENV=production
USE_REAL_DATA=true
ENABLE_SYNTHETIC=false
CACHE_TTL=900
```

Para coleta DataJud:

```env
DATAJUD_API_KEY=sua_chave_nova
```

## Observação técnica
O sistema agora evita travar a interface por fontes externas lentas. As rotas continuam permitindo consulta online sob demanda com parâmetros explícitos.
