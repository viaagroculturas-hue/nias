// Tela 8 — WAR ROOM

import { api } from '../api.js'

let _timer = null

export const warroom = {
  async onEnter() {
    await _render()
    _timer = setInterval(_render, 30_000)
  },
  onLeave() {
    clearInterval(_timer)
    _timer = null
  },
}

async function _render() {
  const alerts = await api.alerts()
  _renderHeader(alerts)
  _renderAlertas(alerts)
  _renderFontes(alerts)
}

function _renderHeader(alerts) {
  const el = document.getElementById('warroom-header')
  if (!el) return

  const list = alerts?.alertas ?? []
  const n1 = list.filter(a => a.nivel === 'N1')
  const n2 = list.filter(a => a.nivel === 'N2')
  const n3 = list.filter(a => a.nivel === 'N3')

  const ts = alerts?._meta?.ts
    ? new Date(alerts._meta.ts).toLocaleString('pt-BR')
    : '--'

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      <div>
        <div style="font-size:22px;font-weight:800;color:${n1.length>0?'var(--danger)':'var(--text)'}">
          ${n1.length > 0 ? '🚨 ALERTA N1 ATIVO' : '● WAR ROOM'}
        </div>
        <div style="font-size:12px;color:var(--text-3)">Última verificação: ${ts}</div>
      </div>
      <div style="display:flex;gap:8px;margin-left:auto">
        <div class="card" style="padding:8px 14px;text-align:center;min-width:70px">
          <div style="font-size:22px;font-weight:700;color:var(--danger)">${n1.length}</div>
          <div style="font-size:10px;font-weight:600;color:var(--danger)">N1 CRÍTICO</div>
        </div>
        <div class="card" style="padding:8px 14px;text-align:center;min-width:70px">
          <div style="font-size:22px;font-weight:700;color:var(--warn)">${n2.length}</div>
          <div style="font-size:10px;font-weight:600;color:var(--warn)">N2 ALERTA</div>
        </div>
        <div class="card" style="padding:8px 14px;text-align:center;min-width:70px">
          <div style="font-size:22px;font-weight:700;color:var(--info)">${n3.length}</div>
          <div style="font-size:10px;font-weight:600;color:var(--info)">N3 ATENÇÃO</div>
        </div>
      </div>
    </div>
  `
}

function _renderAlertas(alerts) {
  const el = document.getElementById('warroom-alertas')
  if (!el) return

  const list = alerts?.alertas ?? []

  if (!list.length) {
    el.innerHTML = `
      <div class="card" style="text-align:center;padding:32px">
        <div style="font-size:32px">✅</div>
        <div style="font-weight:600;margin-top:8px">Nenhum alerta ativo</div>
        <div style="font-size:12px;color:var(--text-2);margin-top:4px">Sistema operando normalmente</div>
      </div>
    `
    return
  }

  // Ordenar: N1 primeiro
  const ordered = [...list].sort((a, b) => a.nivel.localeCompare(b.nivel))

  el.innerHTML = ordered.map(a => `
    <div class="alert-item ${a.nivel}" style="margin-bottom:10px">
      <span class="alert-level">${a.nivel}</span>
      <div class="alert-body">
        <div class="alert-title">${a.titulo}</div>
        <div class="alert-desc">${a.descricao}</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
          ${(a.regioes_afetadas ?? []).map(r => `<span style="background:var(--bg-3);border:1px solid var(--border);border-radius:4px;padding:1px 6px;font-size:11px">${r}</span>`).join('')}
          ${(a.culturas_afetadas ?? []).map(c => `<span style="background:#dcfce7;color:#166534;border-radius:4px;padding:1px 6px;font-size:11px">${c}</span>`).join('')}
        </div>
        <div class="alert-meta">
          FONTE: ${a.fonte}
          · ${a.is_real ? '<span style="color:var(--accent)">● REAL</span>' : '<span style="color:var(--warn)">⚠ REFERENCIAL</span>'}
          · ${new Date(a.timestamp).toLocaleString('pt-BR')}
        </div>
      </div>
    </div>
  `).join('')
}

function _renderFontes(alerts) {
  const el = document.getElementById('warroom-fontes')
  if (!el) return

  const integradas  = alerts?.fontes_integradas  ?? []
  const pendentes   = alerts?.fontes_pendentes    ?? []

  el.innerHTML = `
    <div class="section-title">Status das Fontes de Alerta</div>
    <div class="source-list">
      ${integradas.map(f => `
        <div class="source-row">
          <span class="dot ok">●</span>
          <span class="s-name">${f}</span>
          <span class="data-badge real" style="font-size:10px">integrada</span>
        </div>
      `).join('')}
      ${pendentes.map(f => `
        <div class="source-row">
          <span class="dot down">○</span>
          <span class="s-name" style="color:var(--text-3)">${f}</span>
          <span class="data-badge down" style="font-size:10px">✕ pendente</span>
        </div>
      `).join('')}
    </div>
  `
}
