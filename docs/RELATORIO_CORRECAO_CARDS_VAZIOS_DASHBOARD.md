# Correção — cards e painéis vazios no dashboard

## Problema observado
A tela inicial ainda exibia blocos sem conteúdo, principalmente:
- gráfico NDVI vazio;
- NEWS & MEDIA vazio;
- FEED DE EVENTOS vazio;
- campos com mensagens genéricas sem valor operacional.

## Correção aplicada
1. Inclusão de fallback local rastreável no frontend.
2. Renderização obrigatória de:
   - cards principais;
   - clima;
   - alertas;
   - feed de notícias operacionais;
   - feed de eventos;
   - gráfico NDVI.
3. Quando a API `/api/dashboard/summary` falhar, a tela deixa de ficar vazia e mostra dados locais marcados como fallback/cache.
4. Campos sem fonte ao vivo agora mostram status operacional em vez de ficarem em branco.

## Arquivos alterados
- `index.html`

## Validação
- `node tests/test_syntax.js` executado com sucesso.
