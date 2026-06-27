# NIAS — Endpoints canônicos

> Última atualização: 2026-06-27  
> Convenção: todas as rotas usam o prefixo `/api/`. Rotas legadas com nomes divergentes
> recebem redirect 301 para a forma canônica listada aqui.

---

## Público (sem autenticação)

| Método | Rota canônica | Descrição |
|--------|---------------|-----------|
| GET | `/api/health` | Status de saúde do sistema + 10 fontes de dados |
| GET | `/api/situation/real` | Situation Room — status operacional em tempo real |
| GET | `/api/ceasa/all` | Cotações unificadas CEASA-GO + MG + RN |
| GET | `/api/ceasa/go` | Cotações CEASA-GO (PDF diário) |
| GET | `/api/ceasa/mg` | Cotações CEASA-MG (HTML) |
| GET | `/api/ceasa/rn` | Cotações CEASA-RN (PDF) |
| GET | `/api/cepea` | Indicadores CEPEA/ESALQ (soja, milho, boi, café) |
| GET | `/api/climate` | Dados climáticos Open-Meteo |
| GET | `/api/satellite/analysis` | Análise satelital (NDVI proxy via LAI) |
| GET | `/api/news` | Feed de notícias do agronegócio |
| GET | `/api/flv/*` | Módulo FLV — preços, predições, produtores |
| GET | `/api/intelligence/*` | Motor de inteligência agrícola |
| GET | `/api/nias/demanda` | Demanda agrícola por região |
| GET | `/api/reports` | Relatórios gerados |

## Protegidos (requer `X-API-Key` ou `Authorization: Bearer <token>`)

Variável de ambiente: `NIAS_API_KEY` (desabilitado em dev se não configurada).

| Método | Rota canônica | Descrição |
|--------|---------------|-----------|
| GET | `/api/predictix/live` | PredictX Live — inteligência de mercado em tempo real |
| GET | `/api/predictix/events` | PredictX — eventos de mercado |
| GET | `/api/predictix/intel/*` | Predictix Intelligence — logística, preços, sazonalidade |
| GET | `/api/warroom/*` | War Room — monitoramento de crise |
| GET | `/api/crisis/*` | Crisis Watch — alertas de crise |
| GET | `/api/risk/produtor` | Risk Intelligence — score de risco por produtor |
| GET/POST | `/api/produtor/score` | Score de crédito do produtor |

## Redirects 301 (rotas legadas → canônica)

| Rota legada | → Rota canônica |
|-------------|-----------------|
| `/api/predictx/*` | `/api/predictix/*` |

---

## Convenções

- **Nomenclatura**: sempre `predictix` (com "ix"), nunca `predictx` (sem "i")
- **Versão**: rotas sem versão (`/v1/`, `/v2/`) por enquanto — versionamento futuro via header `X-NIAS-Version`
- **Formato**: todas as respostas são `application/json; charset=utf-8`
- **CORS**: `Access-Control-Allow-Origin: *` em todos os endpoints
- **Qualidade do dado**: todo endpoint inclui campo `_quality` com `status: "LIVE" | "CACHE"` e `cache_age_min`
- **NDVI**: campo `ndvi_source: "PROXY"` indica estimativa via LAI (Open-Meteo), não dado espectral real
