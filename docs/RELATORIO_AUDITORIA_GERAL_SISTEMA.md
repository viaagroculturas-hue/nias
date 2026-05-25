# Relatório — Auditoria Geral, Consolidação e Fontes Reais

Data: 2026-05-24

## Objetivo
Auditar o sistema inteiro, reduzir redundância de abas, bloquear dados sintéticos como se fossem reais e criar uma base de fontes confiáveis para APIs internas.

## Correções aplicadas

1. **Modo autônomo desativado por padrão**
   - Antes: `AUTONOMOUS_MODE = True`, disparando rotinas que podiam gerar/atualizar dados automaticamente.
   - Agora: só ativa com `NIAS_AUTONOMOUS_MODE=1`.

2. **Nova API de auditoria do sistema**
   - `/api/system/audit`
   - `/api/system/sources`
   - Retorna abas mantidas, abas ocultadas, fontes confiáveis, qualidade dos dados locais e alertas de dados sintéticos/proxy.

3. **Registro de fontes confiáveis**
   - Arquivo: `flv/trusted_source_registry.json`
   - Inclui NOAA CPC, IRI, NASA POWER, IBGE SIDRA/PAM/LSPA, CONAB, CEPEA/HF Brasil, FEWS NET, ReliefWeb, World Bank Commodities e CNJ DataJud.

4. **Nova camada backend**
   - Arquivo: `flv/system_audit_api.py`
   - Faz leitura do banco local e identifica tabelas com `is_synthetic`, `data_quality` e `source`.

5. **Aba IA/Auditoria atualizada**
   - Inserido painel “Auditoria do Sistema”.
   - Botão “AUDITAR SISTEMA”.
   - Mostra número de fontes auditáveis, abas ocultas, tabelas FLV e linhas sintéticas/proxy.

6. **Abas redundantes retiradas da navegação principal**
   - Ocultadas/consolidadas: `map`, `logistica`, `warroom`, `flv_insights`, `flv_reports`, `predictix`, `macropolos`, `hyperlocal`, `sentiment`, `esg`.
   - Mantidas: `overview`, `municipal`, `biocommand`, `oferta`, `situation`, `chat`.

7. **Status visual corrigido**
   - Sensores que eram exibidos como “ATIVO” sem validação operacional passaram para “VERIFICAR API”.
   - Evita falsa impressão de telemetria real quando a fonte não foi consultada.

## Política de dados
Nenhum dado estimado, sintético, proxy ou fallback deve ser exibido como dado real. Dados desse tipo devem aparecer como “a validar”, “proxy” ou “indisponível”.

## Validações executadas
- `node test_syntax.js` → OK
- `python3 -m py_compile server.py flv/system_audit_api.py flv/risk_intelligence_api.py flv/predictx_live_api.py flv/situation_real_api.py flv/api/routes.py` → OK
- `build_audit_payload()` → OK

## Observação técnica
A atualização em tempo real depende de internet no ambiente onde o app será executado. O pacote agora contém conectores e registro de fontes oficiais, mas não deve inventar dados quando uma API oficial estiver indisponível.
