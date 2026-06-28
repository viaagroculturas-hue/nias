// Tela 6 — LOGÍSTICA (corredores)

import { api } from '../api.js'

let _logMap = null
let _timer = null

export const logistica = {
  async onEnter() {
    await _render()
    _timer = setInterval(_render, 10 * 60_000)
    _initLogMap()
  },
  onLeave() {
    clearInterval(_timer)
    _timer = null
  },
}

const CORREDORES = [
  {
    id: 'br163',
    nome: 'BR-163',
    descricao: 'Corredor Soja — Sinop/MT → Miritituba/PA',
    extensao_km: 1750,
    volume_ref_mt: 25,
    pontos: [[-12.5, -55.5], [-9.5, -54.8], [-4.5, -56.0]],
    cor: '#f59e0b',
    status: 'operacional',
    alerta: null,
  },
  {
    id: 'br364',
    nome: 'BR-364',
    descricao: 'Corredor Oeste — MT/RO → Porto Velho',
    extensao_km: 1450,
    volume_ref_mt: 12,
    pontos: [[-15.6, -56.1], [-12.7, -60.0], [-8.8, -63.9]],
    cor: '#10b981',
    status: 'operacional',
    alerta: null,
  },
  {
    id: 'ferroeste',
    nome: 'Ferroeste',
    descricao: 'Guarapuava/PR → Cascavel/PR',
    extensao_km: 248,
    volume_ref_mt: 4,
    pontos: [[-25.4, -51.5], [-24.9, -53.5]],
    cor: '#7c3aed',
    status: 'operacional',
    alerta: null,
  },
  {
    id: 'hidrovia_parana',
    nome: 'Hidrovia Paraná',
    descricao: 'Porto de Paranaguá → Interior PR/SP',
    extensao_km: 1300,
    volume_ref_mt: 18,
    pontos: [[-25.5, -48.5], [-23.5, -51.9], [-21.0, -55.0]],
    cor: '#0ea5e9',
    status: 'operacional',
    alerta: null,
  },
]

function _initLogMap() {
  if (_logMap || typeof L === 'undefined') return
  const el = document.getElementById('logistica-leaflet')
  if (!el) return

  _logMap = L.map('logistica-leaflet', { center: [-18, -54], zoom: 4, zoomControl: true })
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap',
  }).addTo(_logMap)

  CORREDORES.forEach(c => {
    const poly = L.polyline(c.pontos, { color: c.cor, weight: 4, opacity: 0.8 })
    poly.bindPopup(`<b>${c.nome}</b><br>${c.descricao}<br>Vol. ref: ${c.volume_ref_mt} Mt`)
    poly.addTo(_logMap)

    // Marcador início
    L.circleMarker(c.pontos[0], { radius: 7, fillColor: c.cor, color: '#fff', weight: 2, fillOpacity: 1 })
      .addTo(_logMap)
    // Marcador fim
    const fim = c.pontos[c.pontos.length - 1]
    L.circleMarker(fim, { radius: 7, fillColor: c.cor, color: '#fff', weight: 2, fillOpacity: 1 })
      .addTo(_logMap)
  })
}

async function _render() {
  const alerts = await api.alerts()
  _renderCards(alerts)
  _renderIEL(alerts)
}

function _renderCards(alerts) {
  const el = document.getElementById('logistica-cards')
  if (!el) return

  el.innerHTML = CORREDORES.map(c => `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
        <div>
          <div style="font-weight:700;font-size:14px" style="color:${c.cor}">${c.nome}</div>
          <div style="font-size:11px;color:var(--text-3)">${c.descricao}</div>
        </div>
        <span style="width:10px;height:10px;border-radius:50%;background:${c.status==='operacional'?'var(--accent)':'var(--danger)'};display:inline-block;margin-top:4px"></span>
      </div>
      <div style="display:flex;gap:12px;font-size:12px;margin-bottom:8px">
        <span><b>${c.extensao_km}</b> km</span>
        <span><b>${c.volume_ref_mt}</b> Mt ref.</span>
        <span style="color:var(--accent)">${c.status}</span>
      </div>
      <div><span class="data-badge fallback">⚠ Volume referencial — ANTT/DNIT pendentes</span></div>
    </div>
  `).join('')
}

function _renderIEL(alerts) {
  const el = document.getElementById('logistica-iel')
  if (!el) return

  const n1 = alerts?.alertas?.filter(a => a.nivel === 'N1').length ?? 0
  const n2 = alerts?.alertas?.filter(a => a.nivel === 'N2').length ?? 0

  // IEL = Índice de Eficiência Logística (calculado dos alertas)
  const iel = Math.max(0, 100 - n1 * 20 - n2 * 10).toFixed(0)
  const cls = iel >= 80 ? 'green' : iel >= 60 ? 'yellow' : 'red'

  el.innerHTML = `
    <div class="card">
      <div class="card-title">IEL — Índice de Eficiência Logística</div>
      <div class="card-value" style="color:${iel>=80?'var(--accent)':iel>=60?'var(--warn)':'var(--danger)'}">${iel}</div>
      <div class="card-sub">Calculado a partir de ${n1+n2} alerta(s) de rota</div>
      <div class="progress-bar" style="margin-top:10px">
        <div class="fill ${cls}" style="width:${iel}%"></div>
      </div>
      <div style="margin-top:8px">
        <span class="data-badge fallback">⚠ IEL estimado — integrar PRF/ANTT para dado real</span>
      </div>
    </div>
  `
}
