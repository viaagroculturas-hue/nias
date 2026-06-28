// Tela 3 — RADAR (oportunidades de arbitragem)

import { api } from '../api.js'

let _timer = null

export const radar = {
  async onEnter() {
    await _render()
    _timer = setInterval(_render, 5 * 60_000)
  },
  onLeave() {
    clearInterval(_timer)
    _timer = null
  },
}

async function _render() {
  const ceasa = await api.ceasa()
  _renderArbitragem(ceasa)
  _renderPortfolio()
}

function _renderArbitragem(ceasa) {
  const el = document.getElementById('radar-arbitragem')
  if (!el) return

  if (!ceasa) {
    el.innerHTML = '<div class="loading-text">Dados CEASA indisponíveis</div>'
    return
  }

  const go = ceasa.go?.cotacoes ?? []
  const mg = ceasa.mg?.cotacoes ?? []
  const rn = ceasa.rn?.cotacoes ?? []

  // Produtos comuns nas 3 praças
  const produtos = ['tomate', 'cebola', 'batata', 'banana', 'laranja', 'manga', 'melao', 'uva']

  const rows = produtos.map(prod => {
    const goCot = go.find(c => c.produto === prod)
    const mgCot = mg.find(c => c.produto === prod)
    const rnCot = rn.find(c => c.produto === prod)

    if (!goCot || !mgCot || !rnCot) return null

    const precos = [goCot.preco, mgCot.preco, rnCot.preco]
    const min = Math.min(...precos)
    const max = Math.max(...precos)
    const margem = ((max - min) / min * 100).toFixed(1)
    const origemMin = min === goCot.preco ? 'GO' : min === mgCot.preco ? 'MG' : 'RN'
    const origemMax = max === goCot.preco ? 'GO' : max === mgCot.preco ? 'MG' : 'RN'

    return { prod, goCot, mgCot, rnCot, margem: parseFloat(margem), origemMin, origemMax }
  }).filter(Boolean)

  rows.sort((a, b) => b.margem - a.margem)

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
      <div class="section-title" style="margin:0">Arbitragem Inter-CEASA</div>
      <span class="data-badge fallback">⚠ Margem estimada — dado referencial</span>
    </div>
    <div class="card" style="padding:0;overflow:hidden">
      <table class="data-table">
        <thead>
          <tr>
            <th>Produto</th>
            <th class="num">CEASA-GO</th>
            <th class="num">CEASA-MG</th>
            <th class="num">CEASA-RN</th>
            <th class="num">Margem est.</th>
            <th>Fluxo</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td style="font-weight:600;text-transform:capitalize">${r.prod}</td>
              <td class="num">R$ ${r.goCot.preco.toFixed(2)}</td>
              <td class="num">R$ ${r.mgCot.preco.toFixed(2)}</td>
              <td class="num">R$ ${r.rnCot.preco.toFixed(2)}</td>
              <td class="num" style="font-weight:700;color:${r.margem>15?'var(--accent)':r.margem>8?'var(--warn)':'var(--text)'}">
                ${r.margem}%
              </td>
              <td style="font-size:12px;color:var(--text-2)">${r.origemMin} → ${r.origemMax}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `
}

function _renderPortfolio() {
  const el = document.getElementById('radar-portfolio')
  if (!el) return

  const riscos = [
    { nome: 'Soja MT — janela colheita',   risco: 25, retorno: 80, tipo: 'oportunidade' },
    { nome: 'Melão RN — exportação UE',    risco: 35, retorno: 70, tipo: 'oportunidade' },
    { nome: 'Uva VSF — colheita precoce',  risco: 45, retorno: 65, tipo: 'moderado' },
    { nome: 'Milho AR — câmbio favorável', risco: 30, retorno: 60, tipo: 'oportunidade' },
    { nome: 'Trigo Sul — El Niño risco',   risco: 70, retorno: 40, tipo: 'risco' },
    { nome: 'Cana SP — queima regulatória',risco: 55, retorno: 35, tipo: 'risco' },
  ]

  el.innerHTML = `
    <div class="section-title">Portfolio de Risco/Retorno</div>
    <div style="display:flex;flex-direction:column;gap:10px">
      ${riscos.map(r => {
        const cls = r.tipo === 'oportunidade' ? 'green' : r.tipo === 'moderado' ? 'yellow' : 'red'
        return `
          <div class="card" style="padding:12px 14px">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
              <span style="font-weight:500;font-size:13px">${r.nome}</span>
              <span class="data-badge fallback" style="font-size:10px">referencial</span>
            </div>
            <div style="display:flex;gap:12px;font-size:12px;color:var(--text-2);margin-bottom:6px">
              <span>Risco: ${r.risco}%</span>
              <span>Retorno est.: ${r.retorno}%</span>
            </div>
            <div class="progress-bar">
              <div class="fill ${cls}" style="width:${r.retorno}%"></div>
            </div>
          </div>
        `
      }).join('')}
    </div>
    <div style="margin-top:8px">
      <span class="data-badge fallback">⚠ Scores calculados com dados referenciais — não constituem recomendação financeira</span>
    </div>
  `
}
