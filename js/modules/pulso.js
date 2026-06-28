// Tela 1 — PULSO (estado vivo)

import { api } from '../api.js'

let _timer = null

export const pulso = {
  async onEnter() {
    await _render()
    _timer = setInterval(_render, 60_000)
  },
  onLeave() {
    clearInterval(_timer)
    _timer = null
  },
}

async function _render() {
  const [health, alerts, ceasa] = await Promise.all([
    api.health(),
    api.alerts(),
    api.ceasa(),
  ])

  _renderKPIs(health, alerts)
  _renderTicker(ceasa)
  _renderClima(health)
  _renderAlertas(alerts)
  _renderSourceStatus(health)
}

function _renderKPIs(health, alerts) {
  const el = document.getElementById('pulso-kpis')
  if (!el) return

  const n1 = alerts?.alertas?.filter(a => a.nivel === 'N1').length ?? 0
  const n2 = alerts?.alertas?.filter(a => a.nivel === 'N2').length ?? 0
  const total = alerts?.alertas?.length ?? 0

  const sources = health?.sources ?? {}
  const okCount = Object.values(sources).filter(s => s.status === 'ok').length
  const totalSrc = Object.keys(sources).length
  const conf = totalSrc ? Math.round((okCount / totalSrc) * 100) : 0

  const sysStatus = health?.status ?? 'unknown'
  const confClass = conf >= 80 ? 'ok' : conf >= 50 ? 'warn' : 'crit'

  const lastTs = health?._meta?.ts
    ? new Date(health._meta.ts).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
    : '--:--'

  el.innerHTML = `
    <div class="card">
      <div class="card-title">Alertas Ativos</div>
      <div class="card-value ${n1 > 0 ? 'crit' : n2 > 0 ? 'warn' : ''}" style="color:${n1>0?'var(--danger)':n2>0?'var(--warn)':'var(--accent)'}">${total}</div>
      <div class="card-sub">${n1} crítico · ${n2} moderado</div>
    </div>
    <div class="card">
      <div class="card-title">Confiança do Sistema</div>
      <div class="card-value ${confClass}" style="color:${conf>=80?'var(--accent)':conf>=50?'var(--warn)':'var(--danger)'}">${conf}%</div>
      <div class="card-sub">${okCount}/${totalSrc} fontes OK</div>
    </div>
    <div class="card">
      <div class="card-title">Status Geral</div>
      <div class="card-value" style="font-size:18px;color:${sysStatus==='ok'?'var(--accent)':sysStatus==='degraded'?'var(--warn)':'var(--danger)'}">${sysStatus.toUpperCase()}</div>
      <div class="card-sub">Sistema NIAS v2</div>
    </div>
    <div class="card">
      <div class="card-title">Última Atualização</div>
      <div class="card-value" style="font-size:20px">${lastTs}</div>
      <div class="card-sub">Hoje</div>
    </div>
  `
}

function _renderTicker(ceasa) {
  const el = document.getElementById('pulso-ticker-inner')
  if (!el || !ceasa) return

  const cotacoes = [
    ...(ceasa.go?.cotacoes ?? []),
    ...(ceasa.mg?.cotacoes ?? []),
  ].slice(0, 20)

  if (!cotacoes.length) { el.innerHTML = '<span style="color:var(--text-3)">Dados CEASA indisponíveis</span>'; return }

  const items = [...cotacoes, ...cotacoes].map(c => `
    <span class="ticker-item">
      <span class="t-prod">${c.produto}</span>
      <span class="t-price">R$ ${c.preco.toFixed(2)}</span>
      <span style="font-size:10px;color:var(--text-3)">${c.unidade}</span>
    </span>
  `).join('<span style="color:var(--border)">|</span>')

  el.innerHTML = items
}

function _renderClima(health) {
  const el = document.getElementById('pulso-clima-grid')
  if (!el) return

  const regioes = [
    { nome: 'Cerrado Central', emoji: '☀️' },
    { nome: 'Pampa Argentina', emoji: '🌤️' },
    { nome: 'Amazônia Sul',    emoji: '🌧️' },
    { nome: 'Sul do Brasil',   emoji: '⛅' },
    { nome: 'MATOPIBA',        emoji: '🌡️' },
    { nome: 'Chaco PY',        emoji: '🌬️' },
    { nome: 'Andes CL/AR',     emoji: '❄️' },
    { nome: 'Nordeste BR',     emoji: '☀️' },
  ]

  el.innerHTML = regioes.map(r => `
    <div class="card clima-card">
      <div class="cc-region">${r.nome}</div>
      <div class="cc-temp">${r.emoji} --°C</div>
      <div class="cc-info">
        <span>-- mm</span>
        <span>-- km/h</span>
      </div>
      <div style="margin-top:6px">
        <span class="data-badge fallback">⚠ Carregando Open-Meteo</span>
      </div>
    </div>
  `).join('')

  // Busca clima real
  api.bioclima().then(data => {
    if (!data?.regioes) return
    const regs = data.regioes
    const cards = el.querySelectorAll('.card')
    cards.forEach((card, i) => {
      const reg = regs[i]
      if (!reg || reg.error) return
      const curr = reg.dados?.current
      if (!curr) return
      card.querySelector('.cc-temp').textContent = `${regioes[i].emoji} ${curr.temperature_2m?.toFixed(1) ?? '--'}°C`
      card.querySelector('.cc-info').innerHTML = `
        <span>${curr.precipitation?.toFixed(1) ?? '--'} mm</span>
        <span>${curr.wind_speed_10m?.toFixed(0) ?? '--'} km/h</span>
      `
      card.querySelector('.data-badge').className = 'data-badge real'
      card.querySelector('.data-badge').textContent = '● REAL · Open-Meteo'
    })
  })
}

function _renderAlertas(alerts) {
  const el = document.getElementById('pulso-alertas')
  if (!el) return

  const list = alerts?.alertas ?? []
  if (!list.length) {
    el.innerHTML = '<div class="loading-text">Nenhum alerta ativo</div>'
    return
  }

  el.innerHTML = list.map(a => `
    <div class="alert-item ${a.nivel}">
      <span class="alert-level">${a.nivel}</span>
      <div class="alert-body">
        <div class="alert-title">${a.titulo}</div>
        <div class="alert-desc">${a.descricao}</div>
        <div class="alert-meta">
          FONTE: ${a.fonte} · ${a.is_real ? '● REAL' : '⚠ REFERENCIAL'}
          · ${new Date(a.timestamp).toLocaleTimeString('pt-BR')}
        </div>
      </div>
    </div>
  `).join('')
}

function _renderSourceStatus(health) {
  const el = document.getElementById('pulso-sources')
  if (!el || !health?.sources) return

  const src = health.sources
  el.innerHTML = Object.entries(src).map(([key, s]) => {
    const dotCls = s.status === 'ok' ? 'ok' : s.status === 'stale' ? 'warn' : 'down'
    const age = s.freshness_s != null ? `${Math.round(s.freshness_s / 60)}min` : 'N/D'
    return `
      <div class="source-row">
        <span class="dot ${dotCls}">●</span>
        <span class="s-name">${key}</span>
        <span class="s-detail">${s.status} · ${age}</span>
      </div>
    `
  }).join('')
}
