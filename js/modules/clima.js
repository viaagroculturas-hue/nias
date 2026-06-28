// Tela 5 — CLIMA (bio-command)

import { api } from '../api.js'

let _climaMap = null
let _timer = null

export const clima = {
  async onEnter() {
    await _render()
    _timer = setInterval(_render, 10 * 60_000)
    _initClimaMap()
  },
  onLeave() {
    clearInterval(_timer)
    _timer = null
  },
}

function _initClimaMap() {
  if (_climaMap || typeof L === 'undefined') return
  const el = document.getElementById('clima-leaflet')
  if (!el) return

  _climaMap = L.map('clima-leaflet', { center: [-15, -55], zoom: 3, zoomControl: false })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
  }).addTo(_climaMap)
}

async function _render() {
  const data = await api.bioclima()
  _renderENSO(data)
  _renderCards(data)
  _renderCorrelacao()
}

function _renderENSO(data) {
  const el = document.getElementById('clima-enso')
  if (!el) return

  const nota = data?.enso_nota ?? ''
  el.innerHTML = `
    <div class="card">
      <div class="card-title">ENSO Status</div>
      <div style="font-size:14px;font-weight:600;color:var(--warn)">⚠ Integração NOAA pendente</div>
      <div style="font-size:12px;color:var(--text-2);margin-top:6px">${data?.enso_status ?? 'N/D'}</div>
      <div style="margin-top:8px"><span class="data-badge down">✕ NOAA ONI · não integrado</span></div>
      <div style="font-size:11px;color:var(--text-3);margin-top:6px">${nota}</div>
    </div>
  `
}

function _renderCards(data) {
  const el = document.getElementById('clima-cards')
  if (!el) return

  const regioes = data?.regioes ?? []
  if (!regioes.length) {
    el.innerHTML = '<div class="loading-text">Dados climáticos indisponíveis</div>'
    return
  }

  el.innerHTML = regioes.map(reg => {
    if (reg.error) return `
      <div class="card clima-card">
        <div class="cc-region">${reg.nome}</div>
        <div style="color:var(--danger);font-size:12px">Erro: ${reg.error}</div>
        <span class="data-badge down">✕ INDISPONÍVEL</span>
      </div>
    `

    const curr = reg.dados?.current ?? {}
    const daily = reg.dados?.daily ?? {}
    const temp = curr.temperature_2m?.toFixed(1) ?? '--'
    const hum  = curr.relative_humidity_2m?.toFixed(0) ?? '--'
    const prec = curr.precipitation?.toFixed(1) ?? '--'
    const wind = curr.wind_speed_10m?.toFixed(0) ?? '--'

    // Precipitação acumulada 30d
    const precSum = (daily.precipitation_sum ?? [])
      .reduce((a, b) => a + (b ?? 0), 0).toFixed(1)

    return `
      <div class="card clima-card">
        <div class="cc-region">${reg.nome}</div>
        <div class="cc-temp">🌡️ ${temp}°C</div>
        <div class="cc-info">
          <span>💧 ${hum}% UR</span>
          <span>🌧 ${prec} mm</span>
          <span>💨 ${wind} km/h</span>
        </div>
        <div style="font-size:11px;color:var(--text-2);margin-top:4px">Prec. 30d: ${precSum} mm</div>
        <div style="margin-top:6px"><span class="data-badge real">● REAL · Open-Meteo</span></div>
      </div>
    `
  }).join('')
}

function _renderCorrelacao() {
  const el = document.getElementById('clima-correlacao')
  if (!el) return

  const correlacoes = [
    { par: 'Temperatura × Tomate',   r: 0.72, dir: 'inversa',  nota: 'Calor > 32°C reduz produção' },
    { par: 'Chuva × Soja MT',        r: 0.68, dir: 'direta',   nota: 'Deficit < 80mm impacta safra' },
    { par: 'Seca × Preço Cebola RN', r: 0.61, dir: 'direta',   nota: 'Veranicos elevam cotação' },
    { par: 'La Niña × Trigo Sul',    r: 0.54, dir: 'inversa',  nota: 'Evento La Niña: -15% produção' },
  ]

  el.innerHTML = `
    <div class="section-title">Correlação Clima × FLV (histórico referencial)</div>
    ${correlacoes.map(c => `
      <div class="card" style="margin-bottom:8px;padding:10px 14px">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
          <span style="font-size:13px;font-weight:500">${c.par}</span>
          <span style="font-weight:700;color:${c.r>0.65?'var(--accent)':'var(--warn)'}">r=${c.r}</span>
        </div>
        <div style="font-size:12px;color:var(--text-2)">${c.nota}</div>
        <div class="progress-bar" style="margin-top:6px">
          <div class="fill ${c.r>0.65?'green':'yellow'}" style="width:${c.r*100}%"></div>
        </div>
        <div style="margin-top:4px"><span class="data-badge fallback">⚠ histórico referencial</span></div>
      </div>
    `).join('')}
  `
}
