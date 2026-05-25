# Atualização da aba MUNICIPAL — América do Sul HF+Granjeiros

Data: 2026-05-24

## Alterações aplicadas

1. **Filtro de países expandido**
   - A aba MUNICIPAL agora permite filtrar polos produtivos de: Brasil, Argentina, Chile, Peru, Colômbia, Equador, Bolívia, Paraguai, Uruguai, Venezuela, Guiana, Suriname e Guiana Francesa.

2. **Produtos hortifrutigranjeiros adicionados aos filtros**
   - Incluídos: mandioca, aspargos, brócolis, pimentão, alface, cenoura, cacau, palta, arándano, arroz, ovos, frango, leite e suínos.

3. **Resumo continental na aba MUNICIPAL**
   - Novo painel superior: quantidade de polos/regiões filtrados, países ativos, lista de produtos e volume estimado agregado em Mt/ano.

4. **Mapa e tabela integrados à base sul-americana**
   - A função `renderChoropleth()` já consumia `MUNICIPAL_DB`; a aba foi atualizada para expor os polos sul-americanos que antes estavam carregados, mas parcialmente invisíveis pela interface.
   - A tabela municipal agora exibe bandeiras de todos os países incluídos e tooltip com produtos associados ao polo.

5. **Popup municipal mais preciso**
   - Rótulos administrativos ampliados: Município/IBGE, Departamento/INDEC, Comuna/INE, Província/INEI, Municipio/DANE, Cantón/INEC, Distrito/DGEEC, etc.

6. **Radar de anomalias atualizado**
   - O feed de anomalias agora reconhece Guiana, Suriname e Guiana Francesa, além dos países já cobertos.

## Escopo e limitação

A base integrada é de polos/regiões produtivas curadas para inteligência geoespacial. Ela não representa cadastro exaustivo de propriedade rural nem substitui consulta oficial dinâmica por país.

## Validação executada

- `node test_syntax.js` → Sintaxe OK.
