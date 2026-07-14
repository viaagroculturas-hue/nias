# VIGÍA — Inteligência Agroestratégica da América do Sul

## Setup rápido

### 1. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Editar `.env` e preencher obrigatoriamente:
```
POSTGRES_PASSWORD=  # openssl rand -hex 32
JWT_SECRET=         # openssl rand -hex 32
ANTHROPIC_API_KEY=  # https://console.anthropic.com
```

### 2. Subir infraestrutura (PostgreSQL + Redis)

```bash
docker compose up -d postgres redis
```

### 3. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Workers Celery (em outro terminal)

```bash
cd backend
celery -A tasks.celery_app worker --loglevel=info
celery -A tasks.celery_app beat --loglevel=info
```

### 6. Iniciar seed de dados

```
POST http://localhost:8000/api/seed/iniciar
```

Acompanhar progresso em:
```
GET http://localhost:8000/api/seed/status
```

## Endpoints principais

| Endpoint | Descrição |
|---|---|
| `GET /api/ping` | Health check simples |
| `GET /api/health/` | Status completo + fontes externas |
| `GET /api/seed/status` | Progresso do seed (10 etapas) |
| `GET /api/radar/` | Radar Vivo — visão consolidada |
| `GET /api/radar/alertas` | Alertas ativos |
| `WS  /api/radar/ws` | WebSocket tempo real (TERRA) |
| `GET /api/relatorio/hoje` | Relatório 05h30 |
| `GET /api/demanda/fatores` | 12 fatores de demanda |
| `GET /api/clima/enso` | Status ENSO atual |
| `GET /api/mapa/municipios` | Municípios SA |
| `GET /api/mercado/cotacoes` | Cotações CEPEA |

## Fontes de dados

| Fonte | Dados | Auth |
|---|---|---|
| IBGE SIDRA | Municípios, PAM produção | Pública |
| BCB SGS | Câmbio, SELIC, IPCA | Pública |
| INMET | Clima, previsão, estações | Pública |
| NOAA CPC | ENSO, índice ONI | Pública |
| CPTEC/INPE | Anomalias precipitação SA | Pública |
| CEPEA/ESALQ | Preços commodities | Scraper público |
| CONAB | Safras, preços mínimos | Pública |
| MDIC ComexStat | Exportações/importações | Pública |
| SMN Argentina | Clima Argentina | Pública |
| DMC Chile | Clima Chile | Pública |
| SENAMHI Peru | Clima Peru | Pública |
| Google Earth Engine | NDVI satélite | Service account |
| Anthropic API | Resumos IA, análise | API key |
| Twilio / Z-API | WhatsApp + SMS | API key |

## Filosofia

```
O VIGÍA não dorme.
Nenhuma plantação invisível.
Nenhum dado sem verificação.
Nenhum alerta sem justificativa.
Nenhuma tela vazia.
Nenhum botão sem função.
Vê antes. Sempre.
```
