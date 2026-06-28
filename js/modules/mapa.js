// Tela 4 — MAPA VIVO (wrapper do mapa Leaflet)

import { initMap, invalidateMap } from '../map.js'

let _initialized = false

export const mapa = {
  onEnter() {
    if (!_initialized) {
      initMap('leaflet-map')
      _initialized = true
    } else {
      // Força resize quando a tela é reexibida
      setTimeout(invalidateMap, 50)
    }
  },
  onLeave() {},
}
