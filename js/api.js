// NIAS v2 — API client com circuit breaker

import { API_BASE, API_KEY } from './config.js'

const _circuit = {}   // { [path]: { failures, openUntil } }

export async function apiFetch(path, params = {}) {
  const base = API_BASE || window.location.origin
  const url = new URL(base + path)
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))

  const circuit = _circuit[path] || { failures: 0, openUntil: 0 }
  if (circuit.openUntil > Date.now()) {
    console.warn(`[NIAS] Circuit open for ${path}`)
    return null
  }

  try {
    const res = await fetch(url.toString(), {
      headers: API_KEY ? { 'X-NIAS-Key': API_KEY } : {},
      signal: AbortSignal.timeout(10000),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()

    _circuit[path] = { failures: 0, openUntil: 0 }

    if (data._meta?.is_fallback) {
      _emitFallback(path, data._meta.source)
    }

    return data
  } catch (err) {
    circuit.failures = (circuit.failures || 0) + 1
    if (circuit.failures >= 3) {
      circuit.openUntil = Date.now() + 5 * 60 * 1000
      console.warn(`[NIAS] Circuit OPEN for ${path} — will retry in 5min`)
    }
    _circuit[path] = circuit
    console.error(`[NIAS] ${path} falhou (${circuit.failures}x):`, err.message)
    return null
  }
}

function _emitFallback(path, source) {
  const ev = new CustomEvent('nias:fallback', { detail: { path, source } })
  document.dispatchEvent(ev)
}

// Endpoints nomeados
export const api = {
  health:    () => apiFetch('/api/health'),
  polos:     (p) => apiFetch('/api/polos', p || {}),
  polo:      (id) => apiFetch(`/api/polo/${id}`),
  ceasa:     () => apiFetch('/api/ceasa/all'),
  cepea:     () => apiFetch('/api/cepea'),
  bioclima:  () => apiFetch('/api/clima/bioclima'),
  alerts:    () => apiFetch('/api/alerts/active'),
  situation: () => apiFetch('/api/situation/real'),
  satellite: (p) => apiFetch('/api/satellite/analysis', p || {}),
}
