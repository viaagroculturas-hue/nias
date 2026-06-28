// Tela 2 — CÉREBRO (inteligência)

import { api } from '../api.js'
import { API_BASE, API_KEY } from '../config.js'

let _timer = null

export const cerebro = {
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
  const [health, alerts, ceasa] = await Promise.all([
    api.health(),
    api.alerts(),
    api.ceasa(),
  ])

  _renderConfidence(health)
  _renderNarrative(health, alerts, ceasa)
  _renderCruzamento(ceasa, alerts)
}

function _renderConfidence(health) {
  const el = document.getElementById('cerebro-confidence')
  if (!el) return

  const sources = health?.sources ?? {}
  const entries = Object.entries(sources)
  const ok = entries.filter(([, s]) => s.status === 'ok').length
  const pct = entries.length ? Math.round((ok / entries.length) * 100) : 0

  const fillCls = pct >= 80 ? 'green' : pct >= 50 ? 'yellow' : 'red'

  el.innerHTML = `
    <div class="confidence-bar">
      <span class="label">Confiança global</span>
      <div class="bar progress-bar">
        <div class="fill ${fillCls}" style="width:${pct}%"></div>
      </div>
      <span class="pct">${pct}%</span>
    </div>
    <div class="source-list">
      ${entries.map(([k, s]) => {
        const cls = s.status === 'ok' ? 'ok' : s.status === 'stale' ? 'warn' : 'down'
        const age = s.freshness_s != null ? `${Math.round(s.freshness_s/60)}min atrás` : 'sem dado'
        return `
          <div class="source-row">
            <span class="dot ${cls}">●</span>
            <span class="s-name">${k}</span>
            <span class="s-detail">${s.status} · ${age}</span>
          </div>
        `
      }).join('')}
    </div>
  `
}

async function _renderNarrative(health, alerts, ceasa) {
  const el = document.getElementById('cerebro-narrative')
  if (!el) return

  el.innerHTML = `<div class="narrative-box"><span style="color:var(--text-3)">Gerando análise de inteligência…</span></div>`

  // Tentar endpoint de narrativa
  try {
    const res = await fetch(`${API_BASE}/api/nias/narrativa`, {
      headers: API_KEY ? { 'X-NIAS-Key': API_KEY } : {},
      signal: AbortSignal.timeout(15000),
    })
    if (res.ok) {
      const data = await res.json()
      el.innerHTML = `
        <div class="narrative-box">${data.narrativa ?? data.text ?? JSON.stringify(data)}</div>
        <span class="data-badge real">● REAL · NIAS-AI · via Claude API</span>
      `
      return
    }
  } catch (_) { /* fallthrough */ }

  // Fallback: narrativa sintetizada localmente
  const sysStatus = health?.status ?? 'unknown'
  const alertCount = alerts?.alertas?.length ?? 0
  const ceasaNota = ceasa?.nota ?? 'dados referenciais'

  el.innerHTML = `
    <div class="narrative-box">Sistema NIAS v2 em modo de observação.

Status: ${sysStatus.toUpperCase()} · ${alertCount} alerta(s) ativo(s).

Fontes de preço: ${ceasaNota}

O cruzamento clima × preços × logística requer endpoint /api/nias/narrativa ativo no backend com integração Claude API.
Configure ANTHROPIC_API_KEY no Render para habilitar narrativa IA real.</div>
    <span class="data-badge fallback">⚠ REFERENCIAL · síntese local · sem Claude API</span>
  `
}

function _renderCruzamento(ceasa, alerts) {
  const el = document.getElementById('cerebro-cruzamento')
  if (!el) return

  const n1 = alerts?.alertas?.filter(a => a.nivel === 'N1') ?? []
  const ceasaOk = ceasa && !ceasa._meta?.is_fallback

  el.innerHTML = `
    <div class="section-title">Cruzamento Clima × Preços × Logística</div>
    <div class="card" style="margin-bottom:10px">
      <div class="card-title">Clima</div>
      <div style="font-size:13px;color:var(--text-2)">
        5 regiões monitoradas via Open-Meteo. ENSO: integração NOAA pendente.
      </div>
      <div style="margin-top:6px"><span class="data-badge real">● Open-Meteo ativo</span></div>
    </div>
    <div class="card" style="margin-bottom:10px">
      <div class="card-title">Preços CEASA</div>
      <div style="font-size:13px;color:var(--text-2)">
        ${ceasaOk ? 'Dados reais disponíveis' : 'Dados referenciais — scraper pendente'}
      </div>
      <div style="margin-top:6px">
        <span class="data-badge fallback">⚠ CEASA GO/MG/RN · referencial estruturado</span>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Alertas de Risco</div>
      <div style="font-size:13px;color:var(--text-2)">
        ${n1.length} alerta(s) N1 · INMET/CEMADEN pendentes de integração
      </div>
      <div style="margin-top:6px">
        <span class="data-badge ${n1.length > 0 ? 'down' : 'fallback'}">
          ${n1.length > 0 ? '✕ N1 ATIVO' : '⚠ REFERENCIAL · Open-Meteo'}
        </span>
      </div>
    </div>
  `
}
