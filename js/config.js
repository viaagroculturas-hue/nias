// NIAS v2 — Configuração global

// Em dev (sem NIAS_API_BASE definido), usa URL relativa (mesmo servidor)
export const API_BASE = window.NIAS_API_BASE || ''
export const API_KEY  = window.NIAS_API_KEY  || ''

export const REFRESH_INTERVAL_MS = 5 * 60 * 1000   // 5 min
export const HEALTH_INTERVAL_MS  = 60 * 1000        // 1 min

export const TILE_OSM = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
export const TILE_SAT = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'

export const MAP_CENTER = [-15, -55]
export const MAP_ZOOM   = 4

// Cores por especialidade de polo
export const POLO_CORES = {
  'grãos':                   '#f59e0b',
  'grãos+logística':         '#f59e0b',
  'grãos+pecuária':          '#f59e0b',
  'grãos+pesquisa':          '#f59e0b',
  'grãos+cerrado':           '#f59e0b',
  'grãos+fronteira':         '#f59e0b',
  'grãos+trigo':             '#f59e0b',
  'grãos+aves':              '#f59e0b',
  'grãos+porto':             '#f59e0b',
  'grãos+erva':              '#f59e0b',
  'grãos+sustentabilidade':  '#10b981',
  'grãos+hortifrutis':       '#10b981',
  'cana+citrus':             '#10b981',
  'café':                    '#92400e',
  'café+grãos':              '#92400e',
  'fruticultura':            '#ec4899',
  'fruticultura_irrigada':   '#ec4899',
  'fruticultura+café':       '#ec4899',
  'fruticultura+vitivinicultura': '#ec4899',
  'horticultura':            '#84cc16',
  'hortifrutis+pesquisa':    '#84cc16',
  'hortifrutis+grãos':       '#84cc16',
  'pecuária':                '#ef4444',
  'vitivinicultura':         '#7c3aed',
  'agroexportação':          '#0ea5e9',
  'banana+cacao':            '#0ea5e9',
}

export const POLO_COR_DEFAULT = '#6366f1'

export function corPolo(especialidade) {
  return POLO_CORES[especialidade] ?? POLO_COR_DEFAULT
}

// Thresholds de alerta
export const THRESHOLDS = {
  CONFIDENCE_WARN:  0.6,
  CONFIDENCE_CRIT:  0.4,
  FRESHNESS_STALE:  3600,   // 1h
  FRESHNESS_DOWN:   10800,  // 3h
}
