# API de antecipação de risco agroclimático/logístico

## O que foi incluído

- Backend: `flv/risk_intelligence_api.py`
- Catálogo de fontes seguras: `flv/safe_sources_risk.json`
- Endpoints:
  - `GET /api/flv/risk/analyze?country=Brasil&product=tomate&days=30`
  - `GET /api/flv/risk/sources`
- Integração visual na aba **IA**:
  - painel de risco de safra, clima, ENSO, fertilizantes e eventos disruptivos
  - filtros por país, produto e janela temporal
  - tabela por polo produtivo
  - cartões com risco máximo, ENSO, eventos e polos analisados

## Fontes seguras antecipatórias

1. NOAA CPC ENSO Diagnostic Discussion / ONI-RONI — El Niño, La Niña e probabilidades.
2. IRI/CPC ENSO Forecast — ensemble probabilístico ENSO.
3. NASA POWER Daily API — precipitação, temperatura, vento e umidade por coordenada.
4. USGS FEWS NET — seca, vegetação e segurança alimentar.
5. FAO GIEWS — alertas de safra, produção e segurança alimentar.
6. FAOSTAT — baseline histórico de produção, área e comércio.
7. ReliefWeb/OCHA API — eventos disruptivos: desastre, conflito, greve, inundação, tempestade.
8. World Bank Commodity Markets — preços globais de energia, fertilizantes e commodities.

## Metodologia

O score é uma triagem de risco, não uma previsão determinística. O cálculo combina:

- clima recente por coordenada — peso principal;
- sinal ENSO — peso secundário;
- eventos disruptivos recentes — peso complementar.

Quando uma fonte online falha, o retorno marca `source_status = fallback_curated`, evitando misturar fallback com dado observado real.

## Limitações

- Fertilizantes, guerras e greves precisam de confirmação em fonte oficial/noticiosa antes de decisão comercial.
- NASA POWER é grade/reanálise por coordenada; não substitui estação meteorológica local auditada.
- ENSO muda probabilidades regionais, mas não determina sozinho uma quebra de safra.
- A API foi criada sem chaves privadas; fontes pagas ou autenticadas não foram usadas.
