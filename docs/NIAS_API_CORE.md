# NIAS API Core v1

API oficial do NIA$ para inteligencia agrocomercial do mercado de hortifruti.

## Base URL

```
/api/nias
```

## Formato de Resposta

### Sucesso
```json
{
  "status": "ok",
  "api": "NIAS API Core",
  "version": "v1",
  "mode": "real_data",
  "data": { ... },
  "meta": {
    "sources": ["CONAB/PROHORT", "Open-Meteo"],
    "updated_at": "2026-06-24T10:00:00",
    "confidence": "alta"
  }
}
```

### Erro
```json
{
  "status": "error",
  "api": "NIAS API Core",
  "version": "v1",
  "message": "Descricao do erro",
  "details": "Detalhes opcionais"
}
```

### Dados Insuficientes
```json
{
  "status": "partial",
  "api": "NIAS API Core",
  "version": "v1",
  "mode": "insufficient_data",
  "message": "Motivo",
  "missing": ["precos recentes"],
  "data": { ... }
}
```

## Modos

| Modo | Descricao |
|------|-----------|
| `real_data` | Dados reais de fontes oficiais |
| `partial` | Dados parciais |
| `fallback` | Dados de fallback |
| `insufficient_data` | Dados insuficientes para a analise |

## Endpoints

### Status e Saude

| Endpoint | Metodo | Descricao | Legacy |
|----------|--------|-----------|--------|
| `/api/nias/status` | GET | Status geral da API | - |
| `/api/nias/health` | GET | Health check com modulos | `/api/health` |
| `/api/nias/docs` | GET | Documentacao da API (JSON) | - |

### Precos

| Endpoint | Metodo | Descricao | Params |
|----------|--------|-----------|--------|
| `/api/nias/prices/latest` | GET | Precos mais recentes | - |
| `/api/nias/prices/history` | GET | Historico de precos | `?product=tomate&limit=50` |

### Clima

| Endpoint | Metodo | Descricao | Legacy |
|----------|--------|-----------|--------|
| `/api/nias/weather/latest` | GET | Dados climaticos recentes | - |
| `/api/nias/weather/risk` | GET | Riscos e alertas climaticos | `/api/climate/alerts` |

### Inteligencia

| Endpoint | Metodo | Descricao | Legacy |
|----------|--------|-----------|--------|
| `/api/nias/intelligence/weather-price` | GET | Correlacao clima x preco | `/api/climate/price-impact` |
| `/api/nias/intelligence/opportunities` | GET | Oportunidades de mercado | `/api/intelligence/opportunities` |
| `/api/nias/intelligence/predictions` | GET | Previsoes de preco | `/api/intelligence/predictions` |
| `/api/nias/intelligence/alerts` | GET | Alertas acionaveis | `/api/intelligence/alerts` |

### Relatorio

| Endpoint | Metodo | Descricao | Legacy |
|----------|--------|-----------|--------|
| `/api/nias/report/daily` | GET | Relatorio executivo diario | `/api/intelligence/report` |

### Fontes e Pipeline

| Endpoint | Metodo | Descricao | Legacy |
|----------|--------|-----------|--------|
| `/api/nias/sources/status` | GET | Status das fontes de dados | `/api/sources/status` |
| `/api/nias/pipeline/status` | GET | Status do pipeline | `/api/pipeline/status` |
| `/api/nias/pipeline/freshness` | GET | Freshness dos dados | `/api/pipeline/freshness` |
| `/api/nias/pipeline/runs` | GET | Historico de execucoes | `/api/pipeline/runs` |

## Fontes de Dados

| Fonte | Status | Descricao |
|-------|--------|-----------|
| CONAB/PROHORT | API REAL | Precos de CEASA semanais |
| Open-Meteo | API REAL | Dados climaticos gratuitos |
| NewsAPI | API REAL | Noticias e risco agregado |
| BCB/ANP | API REAL | Indicadores macroeconomicos |
| CEPEA | FALLBACK | Sem API publica, WAF bloqueia |
| CLIMAPI | FALLBACK | Requer credenciais AgroAPI |

## Exemplos

### Precos mais recentes
```bash
curl https://nias.onrender.com/api/nias/prices/latest
```

### Correlacao clima x preco
```bash
curl https://nias.onrender.com/api/nias/intelligence/weather-price
```

### Status das fontes
```bash
curl https://nias.onrender.com/api/nias/sources/status
```
