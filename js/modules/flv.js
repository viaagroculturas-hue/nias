// Tela 9 — FLV Market Insights

import { api } from '../api.js'

let _timer = null

export const flv = {
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
  _renderKPIs(ceasa)
  _renderArbitragem(ceasa)
  _renderTabela(ceasa)
}

function _renderKPIs(ceasa) {
  const el = document.getElementById('flv-kpis')
  if (!el) return

  const go = ceasa?.go?.cotacoes ?? []
  const mg = ceasa?.mg?.cotacoes ?? []
  const rn = ceasa?.rn?.cotacoes ?? []
  const all = [...go, ...mg, ...rn]

  if (!all.length) {
    el.innerHTML = '<div class="loading-text">Dados indisponíveis</div>'
    return
  }

  // Índice FLV = média dos preços normalizados
  const mediaGO = go.length ? go.reduce((s, c) => s + c.preco, 0) / go.length : 0
  const mediaMG = mg.length ? mg.reduce((s, c) => s + c.preco, 0) / mg.length : 0
  const mediaRN = rn.length ? rn.reduce((s, c) => s + c.preco, 0) / rn.length : 0
  const mediaGeral = [mediaGO, mediaMG, mediaRN].filter(Boolean)
  const indice = mediaGeral.length
    ? (mediaGeral.reduce((a, b) => a + b, 0) / mediaGeral.length).toFixed(2)
    : '--'

  // Spread máximo entre praças
  const spreads = go.map(c => {
    const m = mg.find(x => x.produto === c.produto)
    const r = rn.find(x => x.produto === c.produto)
    const vals = [c.preco, m?.preco, r?.preco].filter(v => v != null)
    return vals.length > 1 ? Math.max(...vals) - Math.min(...vals) : 0
  }).filter(Boolean)

  const maxSpread = spreads.length ? Math.max(...spreads).toFixed(2) : '--'

  const data = ceasa?.go?.data_coleta
    ? new Date(ceasa.go.data_coleta).toLocaleDateString('pt-BR')
    : '--'

  el.innerHTML = `
    <div class="card">
      <div class="card-title">Índice FLV</div>
      <div class="card-value">R$ ${indice}</div>
      <div class="card-sub">Média CEASA GO+MG+RN</div>
      <span class="data-badge fallback">⚠ calculado da média referencial</span>
    </div>
    <div class="card">
      <div class="card-title">Spread Máximo</div>
      <div class="card-value" style="color:var(--warn)">R$ ${maxSpread}</div>
      <div class="card-sub">Maior diferença inter-praça</div>
      <span class="data-badge fallback">⚠ referencial</span>
    </div>
    <div class="card">
      <div class="card-title">Produtos Monitorados</div>
      <div class="card-value">${new Set(all.map(c => c.produto)).size}</div>
      <div class="card-sub">${data}</div>
      <span class="data-badge fallback">⚠ CEASA referencial</span>
    </div>
  `
}

function _renderArbitragem(ceasa) {
  const el = document.getElementById('flv-arbitragem')
  if (!el) return

  const go = ceasa?.go?.cotacoes ?? []
  const mg = ceasa?.mg?.cotacoes ?? []
  const rn = ceasa?.rn?.cotacoes ?? []

  const opps = go.map(c => {
    const m = mg.find(x => x.produto === c.produto)
    const r = rn.find(x => x.produto === c.produto)
    const vals = [
      { praca: 'GO', preco: c.preco },
      ...(m ? [{ praca: 'MG', preco: m.preco }] : []),
      ...(r ? [{ praca: 'RN', preco: r.preco }] : []),
    ]
    const min = vals.reduce((a, b) => a.preco < b.preco ? a : b)
    const max = vals.reduce((a, b) => a.preco > b.preco ? a : b)
    const spread = max.preco - min.preco
    const margem = min.preco > 0 ? ((spread / min.preco) * 100).toFixed(1) : 0
    return { produto: c.produto, min, max, spread, margem: parseFloat(margem), unidade: c.unidade }
  }).filter(o => o.margem > 5).sort((a, b) => b.margem - a.margem).slice(0, 6)

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <div class="section-title" style="margin:0">Oportunidades de Arbitragem FLV</div>
      <span class="data-badge fallback">⚠ referencial</span>
    </div>
    <div class="grid-auto">
      ${opps.map(o => `
        <div class="card">
          <div style="font-weight:700;text-transform:capitalize;margin-bottom:6px">${o.produto}</div>
          <div style="font-size:12px;color:var(--text-2)">
            Comprar ${o.min.praca}: <b>R$ ${o.min.preco.toFixed(2)}</b><br>
            Vender ${o.max.praca}: <b>R$ ${o.max.preco.toFixed(2)}</b>
          </div>
          <div style="margin-top:8px;font-size:14px;font-weight:700;color:${o.margem>20?'var(--accent)':'var(--warn)'}">
            ${o.margem}% · R$ ${o.spread.toFixed(2)}/un
          </div>
          <div style="font-size:10px;color:var(--text-3)">${o.unidade}</div>
          <div class="progress-bar" style="margin-top:6px">
            <div class="fill ${o.margem>20?'green':'yellow'}" style="width:${Math.min(100,o.margem*2)}%"></div>
          </div>
        </div>
      `).join('')}
    </div>
  `
}

function _renderTabela(ceasa) {
  const el = document.getElementById('flv-tabela')
  if (!el) return

  const go = ceasa?.go?.cotacoes ?? []

  el.innerHTML = `
    <div class="section-title">Tabela de Produtos — CEASA-GO (base)</div>
    <div class="card" style="padding:0;overflow:hidden">
      <table class="data-table">
        <thead>
          <tr>
            <th>Produto</th>
            <th class="num">Preço (R$)</th>
            <th class="num">Mín</th>
            <th class="num">Máx</th>
            <th>Unidade</th>
            <th>Qualidade</th>
          </tr>
        </thead>
        <tbody>
          ${go.map(c => `
            <tr>
              <td style="font-weight:500;text-transform:capitalize">${c.produto}</td>
              <td class="num" style="font-weight:600">${c.preco.toFixed(2)}</td>
              <td class="num" style="color:var(--text-3)">${c.min.toFixed(2)}</td>
              <td class="num" style="color:var(--text-3)">${c.max.toFixed(2)}</td>
              <td style="font-size:11px;color:var(--text-3)">${c.unidade}</td>
              <td><span class="data-badge fallback" style="font-size:10px">⚠ ref</span></td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `
}
