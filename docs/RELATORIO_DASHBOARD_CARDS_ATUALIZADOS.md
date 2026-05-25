# Correção do Dashboard Inicial — Cards Atualizados

## Problema corrigido
Os cards iniciais exibiam valores estáticos antigos no HTML, como produção de soja, milho, NDVI, umidade e hortifrutis. Isso dava impressão de tempo real, mas os números não eram recalculados pela base atual.

## Correção aplicada
- Criada a API `/api/dashboard/summary`.
- Criado o módulo `flv/dashboard_summary_api.py`.
- O frontend agora carrega os cards via `DashboardLive.load()`.
- Os valores fixos foram substituídos por `—` até a resposta da API.
- Cada card passa a carregar `fonte`, `data` e `qualidade` no tooltip.
- Atualização automática a cada 15 minutos.

## Regra de qualidade
O dashboard não inventa números. Se não houver dado observado/curado no banco, o card exibe `—` ou status indisponível.

## Fontes usadas pelo resumo
- IBGE/SIDRA ou base oficial local para produção.
- INMET/NASA POWER para clima.
- SATVeg/NASA para NDVI, quando houver dado observado.
- CONAB/CEASA para preços e alertas, quando disponíveis.

## Endpoint
```text
GET /api/dashboard/summary
```

## Resultado esperado
Os cards deixam de mostrar números antigos fixos e passam a refletir a base atual do sistema.
