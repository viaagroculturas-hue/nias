// NIAS v2 — Mapa continental com 46 polos (Leaflet 1.9.4)

import { TILE_OSM, TILE_SAT, MAP_CENTER, MAP_ZOOM, corPolo } from './config.js'
import { api } from './api.js'

// Dados dos 46 polos embutidos (espelho de data/polos_geograficos.py)
const POLOS = [
  // Brasil — Centro-Oeste
  { id:"br_sorriso",            nome:"Sorriso",               pais:"Brasil",    estado:"MT", lat:-12.5490, lon:-55.7209, especialidade:"grãos",              culturas:["soja","milho","algodão"],            area_mha:1.8, volume_ref_mt:6.2  },
  { id:"br_lucas_rio_verde",    nome:"Lucas do Rio Verde",    pais:"Brasil",    estado:"MT", lat:-13.0567, lon:-55.9198, especialidade:"grãos",              culturas:["soja","milho","algodão"],            area_mha:1.4, volume_ref_mt:5.1  },
  { id:"br_nova_mutum",         nome:"Nova Mutum",            pais:"Brasil",    estado:"MT", lat:-13.8306, lon:-56.0819, especialidade:"grãos",              culturas:["soja","milho"],                     area_mha:1.1, volume_ref_mt:4.0  },
  { id:"br_campo_novo_parecis", nome:"Campo Novo do Parecis", pais:"Brasil",    estado:"MT", lat:-13.6725, lon:-57.8946, especialidade:"grãos",              culturas:["soja","algodão","girassol"],         area_mha:1.0, volume_ref_mt:3.5  },
  { id:"br_rondonopolis",       nome:"Rondonópolis",          pais:"Brasil",    estado:"MT", lat:-16.4702, lon:-54.6362, especialidade:"grãos+logística",   culturas:["soja","milho","pecuária"],           area_mha:0.9, volume_ref_mt:3.1  },
  { id:"br_rio_verde",          nome:"Rio Verde",             pais:"Brasil",    estado:"GO", lat:-17.7980, lon:-50.9269, especialidade:"grãos+pecuária",    culturas:["soja","milho","sorgo","pecuária"],   area_mha:0.8, volume_ref_mt:2.8  },
  { id:"br_jatai",              nome:"Jataí",                 pais:"Brasil",    estado:"GO", lat:-17.8793, lon:-51.7156, especialidade:"grãos",              culturas:["soja","milho","sorgo"],             area_mha:0.7, volume_ref_mt:2.4  },
  { id:"br_dourados",           nome:"Dourados",              pais:"Brasil",    estado:"MS", lat:-22.2211, lon:-54.8056, especialidade:"grãos",              culturas:["soja","milho","cana"],              area_mha:0.6, volume_ref_mt:2.1  },
  // Brasil — MATOPIBA
  { id:"br_luis_eduardo_magalhaes", nome:"Luís Eduardo Magalhães", pais:"Brasil", estado:"BA", lat:-12.0961, lon:-45.7897, especialidade:"grãos+cerrado",  culturas:["soja","algodão","milho"],            area_mha:0.9, volume_ref_mt:3.2  },
  { id:"br_barreiras",          nome:"Barreiras",             pais:"Brasil",    estado:"BA", lat:-12.1521, lon:-44.9938, especialidade:"grãos",              culturas:["soja","milho","algodão","café"],    area_mha:0.7, volume_ref_mt:2.5  },
  { id:"br_balsas",             nome:"Balsas",                pais:"Brasil",    estado:"MA", lat:-7.5324,  lon:-46.0356, especialidade:"grãos+fronteira",   culturas:["soja","milho"],                     area_mha:0.6, volume_ref_mt:2.0  },
  { id:"br_paragominas",        nome:"Paragominas",           pais:"Brasil",    estado:"PA", lat:-2.9968,  lon:-47.3558, especialidade:"grãos+sustentabilidade", culturas:["soja","milho","pecuária"],     area_mha:0.4, volume_ref_mt:1.4  },
  // Brasil — Vale do São Francisco
  { id:"br_petrolina",          nome:"Petrolina",             pais:"Brasil",    estado:"PE", lat:-9.3973,  lon:-40.5010, especialidade:"fruticultura_irrigada", culturas:["uva","manga","melão","tomate"], area_mha:0.15,volume_ref_mt:0.8  },
  { id:"br_juazeiro",           nome:"Juazeiro",              pais:"Brasil",    estado:"BA", lat:-9.4278,  lon:-40.5020, especialidade:"fruticultura_irrigada", culturas:["uva","manga","cebola"],         area_mha:0.14,volume_ref_mt:0.75 },
  { id:"br_mossoro",            nome:"Mossoró",               pais:"Brasil",    estado:"RN", lat:-5.1878,  lon:-37.3444, especialidade:"horticultura",       culturas:["melão","melancia","abóbora"],        area_mha:0.08,volume_ref_mt:0.5  },
  // Brasil — Sul
  { id:"br_cascavel",           nome:"Cascavel",              pais:"Brasil",    estado:"PR", lat:-24.9555, lon:-53.4552, especialidade:"grãos+aves",         culturas:["soja","milho","trigo","suínos"],    area_mha:0.5, volume_ref_mt:1.8  },
  { id:"br_londrina",           nome:"Londrina",              pais:"Brasil",    estado:"PR", lat:-23.3045, lon:-51.1696, especialidade:"grãos+pesquisa",     culturas:["soja","milho","café","trigo"],       area_mha:0.4, volume_ref_mt:1.5  },
  { id:"br_maringa",            nome:"Maringá",               pais:"Brasil",    estado:"PR", lat:-23.4205, lon:-51.9333, especialidade:"grãos",              culturas:["soja","milho","café","mandioca"],   area_mha:0.4, volume_ref_mt:1.4  },
  { id:"br_passo_fundo",        nome:"Passo Fundo",           pais:"Brasil",    estado:"RS", lat:-28.2620, lon:-52.4064, especialidade:"grãos+trigo",        culturas:["soja","trigo","milho","aveia"],      area_mha:0.5, volume_ref_mt:1.7  },
  // Brasil — Sudeste
  { id:"br_ribeirao_preto",     nome:"Ribeirão Preto",        pais:"Brasil",    estado:"SP", lat:-21.1767, lon:-47.8208, especialidade:"cana+citrus",        culturas:["cana","laranja","café"],            area_mha:0.6, volume_ref_mt:4.0  },
  { id:"br_franca",             nome:"Franca",                pais:"Brasil",    estado:"SP", lat:-20.5385, lon:-47.4008, especialidade:"café",               culturas:["café","cana"],                      area_mha:0.2, volume_ref_mt:0.6  },
  { id:"br_patrocinio",         nome:"Patrocínio",            pais:"Brasil",    estado:"MG", lat:-18.9429, lon:-46.9939, especialidade:"café+grãos",         culturas:["café","soja","milho"],              area_mha:0.25,volume_ref_mt:0.5  },
  { id:"br_campinas",           nome:"Campinas",              pais:"Brasil",    estado:"SP", lat:-22.9056, lon:-47.0608, especialidade:"hortifrutis+pesquisa",culturas:["laranja","cana","hortifrutis"],    area_mha:0.15,volume_ref_mt:0.8  },
  // Brasil — Pecuária
  { id:"br_xinguara",           nome:"Xinguara",              pais:"Brasil",    estado:"PA", lat:-7.1000,  lon:-49.9500, especialidade:"pecuária",           culturas:["pecuária","soja"],                  area_mha:1.2, volume_ref_mt:0.4  },
  // Argentina
  { id:"ar_rosario",            nome:"Rosario",               pais:"Argentina", estado:"SF", lat:-32.9442, lon:-60.6505, especialidade:"grãos+porto",        culturas:["soja","trigo","milho","girassol"],  area_mha:2.0, volume_ref_mt:8.0  },
  { id:"ar_cordoba",            nome:"Córdoba",               pais:"Argentina", estado:"CBA",lat:-31.4201, lon:-64.1888, especialidade:"grãos+pecuária",     culturas:["soja","milho","trigo","maní"],      area_mha:1.5, volume_ref_mt:5.5  },
  { id:"ar_pergamino",          nome:"Pergamino",             pais:"Argentina", estado:"BA", lat:-33.8882, lon:-60.5704, especialidade:"grãos",              culturas:["soja","milho","trigo"],             area_mha:0.8, volume_ref_mt:2.8  },
  { id:"ar_venado_tuerto",      nome:"Venado Tuerto",         pais:"Argentina", estado:"SF", lat:-33.7454, lon:-61.9684, especialidade:"grãos",              culturas:["soja","milho","trigo","girassol"],  area_mha:0.7, volume_ref_mt:2.5  },
  { id:"ar_bahia_blanca",       nome:"Bahía Blanca",          pais:"Argentina", estado:"BA", lat:-38.7183, lon:-62.2663, especialidade:"grãos+porto",        culturas:["trigo","girassol","cevada"],         area_mha:0.9, volume_ref_mt:3.0  },
  { id:"ar_tucuman",            nome:"Tucumán",               pais:"Argentina", estado:"TUC",lat:-26.8241, lon:-65.2226, especialidade:"cana+citrus",        culturas:["cana","limão","tabaco","soja"],      area_mha:0.3, volume_ref_mt:1.8  },
  { id:"ar_mendoza",            nome:"Mendoza",               pais:"Argentina", estado:"MZA",lat:-32.8908, lon:-68.8272, especialidade:"vitivinicultura",    culturas:["uva","vinho","azeite","alho"],       area_mha:0.15,volume_ref_mt:0.9  },
  { id:"ar_salta",              nome:"Salta",                 pais:"Argentina", estado:"SAL",lat:-24.7859, lon:-65.4116, especialidade:"grãos+hortifrutis",  culturas:["soja","tabaco","pimentão","feijão"], area_mha:0.5, volume_ref_mt:1.5  },
  // Paraguai
  { id:"py_alto_parana",        nome:"Alto Paraná",           pais:"Paraguai",  estado:"AP", lat:-25.5094, lon:-54.6100, especialidade:"grãos",              culturas:["soja","milho","trigo"],             area_mha:1.2, volume_ref_mt:4.0  },
  { id:"py_itapua",             nome:"Itapúa",                pais:"Paraguai",  estado:"ITA",lat:-27.3326, lon:-55.8666, especialidade:"grãos+erva",         culturas:["soja","trigo","milho","erva-mate"], area_mha:0.8, volume_ref_mt:2.5  },
  { id:"py_caaguazu",           nome:"Caaguazú",              pais:"Paraguai",  estado:"CAG",lat:-25.4367, lon:-56.0194, especialidade:"grãos",              culturas:["soja","milho","trigo"],             area_mha:0.6, volume_ref_mt:2.0  },
  // Uruguai
  { id:"uy_paysandu",           nome:"Paysandú",              pais:"Uruguai",   estado:"PY", lat:-32.3220, lon:-58.0756, especialidade:"grãos",              culturas:["soja","trigo","milho","arroz"],      area_mha:0.4, volume_ref_mt:1.2  },
  { id:"uy_rivera",             nome:"Rivera",                pais:"Uruguai",   estado:"RIV",lat:-30.9020, lon:-55.5500, especialidade:"grãos+pecuária",     culturas:["soja","pecuária","florestal"],       area_mha:0.3, volume_ref_mt:0.8  },
  // Bolívia
  { id:"bo_santa_cruz",         nome:"Santa Cruz de la Sierra",pais:"Bolívia", estado:"SC", lat:-17.7833, lon:-63.1821, especialidade:"grãos",              culturas:["soja","girassol","sorgo","milho"],   area_mha:1.5, volume_ref_mt:4.5  },
  // Peru
  { id:"pe_ica",                nome:"Ica",                   pais:"Peru",      estado:"ICA",lat:-14.0678, lon:-75.7286, especialidade:"agroexportação",     culturas:["uva","aspargo","algodão","tomate"],  area_mha:0.1, volume_ref_mt:0.4  },
  { id:"pe_piura",              nome:"Piura",                 pais:"Peru",      estado:"PIU",lat:-5.1945,  lon:-80.6328, especialidade:"fruticultura",       culturas:["manga","limão","banana","algodão"],  area_mha:0.12,volume_ref_mt:0.5  },
  // Colômbia
  { id:"co_llanos_orientales",  nome:"Llanos Orientales",     pais:"Colômbia",  estado:"MET",lat:4.1531,   lon:-73.6347, especialidade:"grãos+pecuária",     culturas:["arroz","milho","palma","pecuária"],  area_mha:0.8, volume_ref_mt:1.8  },
  { id:"co_magdalena",          nome:"Santa Marta / Magdalena",pais:"Colômbia", estado:"MAG",lat:11.2404,  lon:-74.2110, especialidade:"fruticultura+café",  culturas:["banana","palma","café"],             area_mha:0.2, volume_ref_mt:0.7  },
  // Venezuela
  { id:"ve_llanos",             nome:"Llanos Ocidentais",     pais:"Venezuela", estado:"BAR",lat:8.6230,   lon:-70.2079, especialidade:"grãos+pecuária",     culturas:["milho","arroz","sorgo","pecuária"],  area_mha:0.6, volume_ref_mt:1.2  },
  // Chile
  { id:"cl_valle_central",      nome:"Valle Central",         pais:"Chile",     estado:"OHI",lat:-34.5755, lon:-71.0022, especialidade:"fruticultura+vitivinicultura", culturas:["uva","cereja","maçã","paltas"], area_mha:0.3, volume_ref_mt:1.5  },
  { id:"cl_atacama_horticultura",nome:"Valle de Atacama",     pais:"Chile",     estado:"ATA",lat:-27.3668, lon:-70.3313, especialidade:"fruticultura_irrigada", culturas:["uva de mesa","azeitona","pimentão"], area_mha:0.08,volume_ref_mt:0.25 },
  // Equador
  { id:"ec_guayas",             nome:"Guayas",                pais:"Equador",   estado:"GUA",lat:-2.1893,  lon:-79.8875, especialidade:"banana+cacao",       culturas:["banana","cacao","camarão","arroz"],  area_mha:0.25,volume_ref_mt:2.0  },
]

export { POLOS }

let _map = null
let _markerLayer = null
let _alertLayer  = null
let _tileOSM = null
let _tileSAT = null

export function initMap(containerId) {
  if (_map) { _map.invalidateSize(); return }

  _map = L.map(containerId, {
    center: MAP_CENTER,
    zoom:   MAP_ZOOM,
    zoomControl: true,
  })

  _tileOSM = L.tileLayer(TILE_OSM, {
    attribution: '© OpenStreetMap',
    maxZoom: 18,
  }).addTo(_map)

  _tileSAT = L.tileLayer(TILE_SAT, {
    attribution: '© Esri',
    maxZoom: 18,
  })

  _markerLayer = L.layerGroup().addTo(_map)
  _alertLayer  = L.layerGroup()

  _plotPolos(POLOS)
  _buildHUDs()
  _wireControls()
}

function _plotPolos(polos) {
  _markerLayer.clearLayers()
  polos.forEach(polo => {
    const cor = corPolo(polo.especialidade)

    // Círculo externo — pulso sonar
    const ring = L.circleMarker([polo.lat, polo.lon], {
      radius: 16,
      fillColor: cor,
      fillOpacity: 0.12,
      color: cor,
      weight: 1,
      opacity: 0.5,
      interactive: false,
      className: 'sonar-ring',
    })

    // Marcador principal
    const marker = L.circleMarker([polo.lat, polo.lon], {
      radius: 8,
      fillColor: cor,
      color: '#fff',
      weight: 2,
      opacity: 1,
      fillOpacity: 0.9,
    })

    marker.bindPopup(_buildPopup(polo), { maxWidth: 280 })

    marker.on('popupopen', () => {
      _fetchNDVI(polo)
      ring.setStyle({ fillOpacity: 0.25, opacity: 0.8 })
    })
    marker.on('popupclose', () => {
      ring.setStyle({ fillOpacity: 0.12, opacity: 0.5 })
    })

    _markerLayer.addLayer(ring)
    _markerLayer.addLayer(marker)
  })
}

function _buildPopup(polo) {
  return `
    <div class="polo-popup">
      <h3>${polo.nome} — ${polo.pais}</h3>
      <div class="polo-culturas">${polo.culturas.join(' · ')}</div>
      <div class="polo-kpis">
        <span>Área: ${polo.area_mha} Mha</span>
        <span>Vol. ref: ${polo.volume_ref_mt} Mt</span>
      </div>
      <div class="polo-ndvi" id="ndvi-${polo.id}">
        <span style="color:#94a3b8">Carregando NDVI proxy…</span>
      </div>
      <button onclick="window.__niasPoloDetail('${polo.id}')">Ver análise completa →</button>
    </div>
  `
}

async function _fetchNDVI(polo) {
  const el = document.getElementById(`ndvi-${polo.id}`)
  if (!el) return
  const data = await api.polo(polo.id)
  if (!data) {
    el.innerHTML = '<span style="color:#dc2626">NDVI indisponível</span>'
    return
  }
  const ndvi = data.ndvi
  if (ndvi?.error) {
    el.innerHTML = `<span style="color:#dc2626">Erro: ${ndvi.error}</span>`
    return
  }
  const val = ndvi?.ndvi_proxy != null ? ndvi.ndvi_proxy.toFixed(3) : 'N/D'
  el.innerHTML = `
    <b>NDVI proxy:</b> ${val}
    <span style="font-size:10px;color:#92400e;display:block;margin-top:2px">
      ⚠ Estimativa LAI Open-Meteo — desvio ±15%
    </span>
  `
}

function _buildHUDs() {
  // HUD satélite — painel esquerdo
  const hudSat = document.getElementById('map-hud-sat')
  if (hudSat) {
    hudSat.innerHTML = `
      <div class="hud-title">Fontes de Imagem</div>
      <div class="sat-row"><span class="sat-dot online">●</span><span class="sat-name">Sentinel-2A</span><span class="sat-info">10m · Cache 8h</span></div>
      <div class="sat-row"><span class="sat-dot online">●</span><span class="sat-name">Open-Meteo</span><span class="sat-info">LAI proxy · Cache 1h</span></div>
      <div class="sat-row"><span class="sat-dot offline">○</span><span class="sat-name">PlanetScope</span><span class="sat-info">Não integrado</span></div>
    `
  }
}

function _wireControls() {
  // Toggle camadas
  document.getElementById('layer-polos')?.addEventListener('change', e => {
    e.target.checked ? _markerLayer.addTo(_map) : _map.removeLayer(_markerLayer)
  })
  document.getElementById('layer-alerts')?.addEventListener('change', e => {
    e.target.checked ? _alertLayer.addTo(_map) : _map.removeLayer(_alertLayer)
  })
  document.getElementById('layer-sat')?.addEventListener('change', e => {
    if (e.target.checked) {
      _map.removeLayer(_tileOSM)
      _tileSAT.addTo(_map)
    } else {
      _map.removeLayer(_tileSAT)
      _tileOSM.addTo(_map)
    }
  })

  // Filtro por cultura
  document.getElementById('filter-cultura')?.addEventListener('change', e => {
    const val = e.target.value
    const filtered = val ? POLOS.filter(p => p.culturas.some(c => c.toLowerCase().includes(val))) : POLOS
    _plotPolos(filtered)
  })
}

export function invalidateMap() {
  _map?.invalidateSize()
}

// Exposto globalmente para o botão do popup
window.__niasPoloDetail = async (id) => {
  const data = await api.polo(id)
  if (!data) return
  alert(`${data.nome}\nNDVI proxy: ${data.ndvi?.ndvi_proxy ?? 'N/D'}\nÚltima atualização: ${data.data_hora}`)
}
