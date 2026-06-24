# NIAS — Estrutura organizada para GitHub/Render

Suba esta pasta inteira no repositório `viaagroculturas-hue/nias`.

## Estrutura principal

```text
nias/
├── server.py              # servidor principal usado pelo Render
├── app.py                 # compatibilidade
├── index.html             # frontend principal
├── requirements.txt       # dependências Python
├── Procfile               # web: python server.py
├── render.yaml            # configuração Render
├── flv/                   # backend, APIs, coletores, modelos e bases internas
├── data/                  # dados locais, schema, cache e arquivos auxiliares
├── static/                # JS, imagens e assets soltos
├── tests/                 # testes e validações
├── scripts/               # scripts administrativos/seed/migração
└── docs/                  # relatórios técnicos e histórico de correções
```

## Arquivos que devem permanecer na raiz

- `server.py`
- `app.py`
- `index.html`
- `requirements.txt`
- `Procfile`
- `render.yaml`
- `.gitignore`

## Deploy no Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
python server.py
```

## Variáveis recomendadas

```env
NIAS_AUTONOMOUS_MODE=0
USE_REAL_DATA=true
ENABLE_SYNTHETIC=false
CACHE_TTL=900
```

## Observação

Os relatórios e scripts foram movidos para `docs/` e `scripts/` para limpar a raiz do GitHub. O `index.html` ficou na raiz porque o servidor atual serve arquivos estáticos a partir da raiz do projeto.
