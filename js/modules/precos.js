// Tela 7 — PREÇOS (mercado real)

import { api } from '../api.js'

let _timer = null

export const precos = {
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
  const [ceasa, cepea] = await Promise.all([api.ceasa(), api.cepea()])
  _renderCepea(cepea)
  _renderCeasa(ceasa)
  _renderUSD(cepea)
}

function _renderCepea(cepea) {
  const el = document.getElementById('precos-cepea')
  if (!el) return

  const commodities = [
    { key: 'soja_sc60kg',       label: 'Soja',      unidade: 'sc 60kg' },
    { key: 'milho_sc60kg',      label: 'Milho',     unidade: 'sc 60kg' },
    { key: 'boi_gordo_arroba',  label: 'Boi Gordo', unidade: '@' },
    { key: 'cafe_sc60kg',       label: 'Café',      unidade: 'sc 60kg' },
  ]

  el.innerHTML = commodities.map(c => {
    const d = cepea?.[c.key]
    const valor = d?.valor != null ? `R$ ${d.valor.toFixed(2)}` : '—'
    const isReal = d?.is_real
    const fonte = d?.fonte ?? 'CEPEA ESALQ'

    return `
      <div class="card">
        <div class="card-title">CEPEA · ${c.label}</div>
        <div class="card-value" style="font-size:22px;color:${isReal?'var(--text)':'var(--text-3)'}">${valor}</div>
        <div class="card-sub">${c.unidade} · ${fonte}</div>
        <div style="margin-top:8px">
          <span class="data-badge ${isReal?'real':'down'}">
            ${isReal ? '● REAL · CEPEA ESALQ' : '✕ SCRAPER PENDENTE · sem dado real'}
          </span>
        </div>
      </div>
    `
  }).join('')
}

function _renderCeasa(ceasa) {
  const el = document.getElementById('precos-ceasa-table')
  if (!el) return

  if (!ceasa) {
    el.innerHTML = '<div class="loading-text">CEASA indisponível</div>'
    return
  }

  const go = ceasa.go?.cotacoes ?? []
  const mg = ceasa.mg?.cotacoes ?? []
  const rn = ceasa.rn?.cotacoes ?? []
  const data = ceasa.go?.data_coleta ?? ceasa._meta?.ts ?? ''
  const freshness = data ? new Date(data).toLocaleString('pt-BR') : '--'

  const produtos = [...new Set([...go, ...mg, ...rn].map(c => c.produto))].sort()

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
      <div class="section-title" style="margin:0">CEASA Unificado</div>
      <span class="data-badge fallback">⚠ REFERENCIAL · atualizado ${freshness}</span>
    </div>
    <div class="card" style="padding:0;overflow:hidden">
      <table class="data-table">
        <thead>
          <tr>
            <th>Produto</th>
            <th class="num">GO (R$)</th>
            <th class="num">MG (R$)</th>
            <th class="num">RN (R$)</th>
            <th>Unidade</th>
          </tr>
        </thead>
        <tbody>
          ${produtos.map(prod => {
            const g = go.find(c => c.produto === prod)
            const m = mg.find(c => c.produto === prod)
            const r = rn.find(c => c.produto === prod)
            return `
              <tr>
                <td style="font-weight:500;text-transform:capitalize">${prod}</td>
                <td class="num">${g ? g.preco.toFixed(2) : '—'}</td>
                <td class="num">${m ? m.preco.toFixed(2) : '—'}</td>
                <td class="num">${r ? r.preco.toFixed(2) : '—'}</td>
                <td style="font-size:11px;color:var(--text-3)">${g?.unidade ?? m?.unidade ?? r?.unidade ?? ''}</td>
              </tr>
            `
          }).join('')}
        </tbody>
      </table>
    </div>
    <div style="margin-top:8px;font-size:11px;color:var(--text-3)">${ceasa.nota ?? ''}</div>
  `
}

function _renderUSD(cepea) {
  const el = document.getElementById('precos-usd')
  if (!el) return

  const usd = cepea?.usd_brl
  if (!usd) { el.innerHTML = ''; return }

  el.innerHTML = `
    <div class="card">
      <div class="card-title">USD / BRL · Banco Central do Brasil</div>
      <div class="card-value" style="font-size:24px">${usd.valor != null ? `R$ ${usd.valor.toFixed(4)}` : '—'}</div>
      <div class="card-sub">1 USD · ${usd.fonte}</div>
      <div style="margin-top:8px">
        <span class="data-badge ${usd.is_real ? 'real' : 'fallback'}">
          ${usd.is_real ? '● REAL · BCB API' : '⚠ FALLBACK · valor de referência'}
        </span>
      </div>
    </div>
  `
}
