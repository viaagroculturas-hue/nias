## Objetivo
Conectar a API IBGE SIDRA v3 (já funcional via `fetchSidraProduction`) aos painéis **BIO-COMMAND** e **Análise Municipal**, eliminando dependência de dados sintéticos quando a API responde.

---

## Mudanças

### 1. BIO-COMMAND — Enriquecer sonar com VBP real do SIDRA

**Arquivo:** `nias.html` ~L5250-5262 (`initBioCommand` sonar loop)

- Ao inicializar, fazer `fetchSidraProduction('soja', 'last')` (cultura padrão) e criar lookup `ibgeCode → VBP`
- Adicionar `_bcSidraVBP` ao marcador para exibir no painel direito
- No tooltip do sonar, incluir VBP quando disponível

**Arquivo:** `nias.html` ~L5282-5310 (`bcOpenRight`)

- Se `m.ibgeCode` e `_bcSidraCache[m.ibgeCode]` existirem, mostrar:
  - `VBP IBGE: R$ xxx mil` (variável 35)
  - `Produção: xxx t` (variável 216 se buscarmos)
  - Badge `SIDRA API REAL` verde ou `SINTÉTICO` amarelo
- Adicionar linha `Fonte: IBGE/SIDRA {ano}` no rodapé da biópsia

### 2. BIO-COMMAND — `bcTrocarCultura` busca SIDRA por cultura

**Arquivo:** `nias.html` ~L5361-5373 (`bcTrocarCultura`)

- Tornar a função `async`
- Ao trocar cultura, chamar `fetchSidraProduction(cult, 'last')`
- Armazenar resultado em `window._bcSidraData`
- Ajustar tamanho/brilho do sonar baseado no VBP real (municípios com maior VBP = sonar maior)
- Fallback: manter opacidade visual se SIDRA falhar

### 3. Análise Municipal — `trocarCultura` já usa SIDRA ✓

**Já implementado** em L2846-2878. A função `trocarCultura` chama `fetchSidraProduction` e renderiza via `renderSidraLayer`. **Apenas ajustar:**

- Variável `var:35` (VBP R$ mil) já está no `SIDRA_CULTURES` — confirmar que o endpoint v3 retorna dados
- Adicionar variável `216` (quantidade produzida em toneladas) como segunda consulta para enriquecer a tabela `buildMunTable`
- Na tabela Rm, mostrar coluna "VBP IBGE" ao lado do Rm estimado quando dados SIDRA disponíveis

### 4. `bcOpenRight` — Mostrar previsão de 7 dias (Open-Meteo + SIDRA)

**Arquivo:** `nias.html` ~L5282 (`bcOpenRight`)

- Se `m._et0_7d` existe (já preenchido pelo Open-Meteo Multi), mostrar mini-gráfico de ET0 (evapotranspiração)
- Se `_bcSidraData` tem VBP para o município, mostrar valor financeiro em risco usando fórmula: `VaR = VBP × (1 - NDVI/0.7)`

### 5. Auto-fetch SIDRA no `niasLoadRealData`

**Arquivo:** `nias.html` ~L6100 (`niasLoadRealData`)

- Adicionar fetch SIDRA para soja (cultura mais relevante) como dado de base
- Armazenar em `window._niasSidraBase` para uso no BIO-COMMAND e War Room
- Atualizar status bar: `SIDRA: API REAL (4.823 municípios)`

---

## Verificação

| Step | Targets | Verificação |
|------|---------|-------------|
| 1 | `initBioCommand` L5250 | Sonar tooltip mostra VBP quando SIDRA responde |
| 2 | `bcTrocarCultura` L5361 | Trocar cultura no BIO-COMMAND busca SIDRA v3 |
| 3 | `trocarCultura` L2846 | Análise Municipal renderiza com endpoint v3 correto |
| 4 | `bcOpenRight` L5282 | Painel direito mostra VBP IBGE + fonte |
| 5 | `niasLoadRealData` L6100 | Status bar mostra SIDRA: API REAL |
