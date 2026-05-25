# Melhoria dos mapas — contornos de países e estados/províncias

## Alterações aplicadas

- Adicionada camada de contornos reais de países da América do Sul nos mapas principais.
- Adicionada camada de estados/províncias/departamentos via `geoBoundaries` ADM1.
- Adicionada camada de países via `geoBoundaries` ADM0.
- Aplicado o mesmo padrão na aba Municipal.
- Aplicado contorno real para EUA, México e Canadá no PredictX, para análise de Copa do Mundo 2026.
- Mantido fallback local: se a fonte externa não carregar, os polígonos produtivos continuam funcionando.

## Fontes usadas em tempo de execução

- geoBoundaries Open: limites administrativos ADM0 e ADM1.
- CartoDB Dark Matter / OpenStreetMap: base cartográfica.

## Observação técnica

As camadas reais são carregadas no navegador via `fetch`. Portanto, precisam de conexão externa ativa. O sistema não trava se a fonte externa estiver indisponível; apenas mantém os mapas produtivos internos sem as divisas oficiais.
