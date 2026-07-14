'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

type Camada = 'municipios' | 'alertas' | 'ndvi'

interface AlertaGeo {
  id: string
  tipo: string
  nivel: 'critico' | 'atencao' | 'info'
  titulo: string
  descricao: string
  acao_recomendada: string
  confianca_pct: number
  impacto_financeiro: number
  fontes: string[]
  lat: number
  lon: number
  municipio: string
  estado: string
  pais: string
  created_at: string
}

interface NdviGeo {
  municipio_id: string
  municipio: string
  lat: number
  lon: number
  ndvi_medio: number
  fase_estimada: string
  anomalia_detectada: boolean
  data_imagem: string
  satelite: string
}

const COR_NIVEL: Record<string, string> = {
  critico: '#ef4444',
  atencao: '#f59e0b',
  info:    '#60a5fa',
}

function ndviParaCor(ndvi: number): string {
  // 0.0 → marrom, 0.3 → amarelo, 0.6 → verde, 0.8+ → verde escuro
  if (ndvi < 0.1)  return '#8B4513'
  if (ndvi < 0.2)  return '#D2B48C'
  if (ndvi < 0.3)  return '#DAA520'
  if (ndvi < 0.45) return '#9ACD32'
  if (ndvi < 0.6)  return '#32CD32'
  if (ndvi < 0.75) return '#228B22'
  return '#006400'
}

function PainelAlerta({
  alerta,
  onFechar,
}: {
  alerta: AlertaGeo
  onFechar: () => void
}) {
  const corBorda = alerta.nivel === 'critico' ? 'border-red-500/40' : 'border-amber-500/40'

  return (
    <div className={`absolute bottom-4 left-4 right-4 md:top-4 md:right-4 md:bottom-auto md:left-auto md:w-80 z-20 bg-black/95 border ${corBorda} rounded p-5 shadow-2xl`}>
      <div className="flex items-start justify-between mb-3">
        <span className={`text-xs px-2 py-0.5 rounded border ${
          alerta.nivel === 'critico'
            ? 'border-red-500/50 text-red-400'
            : 'border-amber-500/50 text-amber-400'
        }`}>{alerta.nivel.toUpperCase()}</span>
        <button
          onClick={onFechar}
          className="text-white/30 hover:text-white/70 text-lg leading-none ml-2"
        >
          ×
        </button>
      </div>

      <div className="text-white text-sm font-medium mb-2 leading-snug">{alerta.titulo}</div>

      <div className="text-white/50 text-xs mb-3 leading-relaxed">{alerta.descricao}</div>

      <div className="flex flex-wrap gap-3 text-xs text-white/35 mb-3">
        <span>📍 {alerta.municipio}{alerta.estado ? `, ${alerta.estado}` : ''}</span>
        <span>Conf. {alerta.confianca_pct.toFixed(0)}%</span>
        {alerta.impacto_financeiro > 0 && (
          <span>R$ {alerta.impacto_financeiro.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}</span>
        )}
      </div>

      {alerta.acao_recomendada && (
        <div className="border-t border-white/10 pt-3 text-xs text-white/60">
          → {alerta.acao_recomendada}
        </div>
      )}

      {alerta.fontes?.length > 0 && (
        <div className="text-white/20 text-xs mt-2">{alerta.fontes.join(' · ')}</div>
      )}
    </div>
  )
}

function PainelNdvi({ ndvi, onFechar }: { ndvi: NdviGeo; onFechar: () => void }) {
  return (
    <div className="absolute bottom-4 left-4 right-4 md:top-4 md:right-4 md:bottom-auto md:left-auto md:w-72 z-20 bg-black/95 border border-white/15 rounded p-5 shadow-2xl">
      <div className="flex items-start justify-between mb-3">
        <div className="text-xs text-white/30 tracking-widest">NDVI · {ndvi.satelite}</div>
        <button onClick={onFechar} className="text-white/30 hover:text-white/70 text-lg leading-none">×</button>
      </div>

      <div className="text-white text-sm font-medium mb-1">{ndvi.municipio}</div>

      <div className="flex items-center gap-3 mb-4 mt-3">
        <div
          className="w-10 h-10 rounded flex-shrink-0"
          style={{ background: ndviParaCor(ndvi.ndvi_medio) }}
        />
        <div>
          <div className="text-2xl font-light text-white tabular-nums">
            {ndvi.ndvi_medio.toFixed(3)}
          </div>
          <div className="text-white/40 text-xs">{ndvi.fase_estimada?.replace('_', ' ')}</div>
        </div>
      </div>

      {ndvi.anomalia_detectada && (
        <div className="border border-amber-500/40 bg-amber-500/5 rounded p-2 text-amber-400 text-xs mb-3">
          ⚠ Anomalia detectada
        </div>
      )}

      <div className="text-white/25 text-xs">{ndvi.data_imagem?.slice(0, 10)}</div>
    </div>
  )
}

export default function MapaInterativo() {
  const mapRef     = useRef<any>(null)
  const layersRef  = useRef<{ municipios: any[]; alertas: any[]; ndvi: any[] }>({
    municipios: [], alertas: [], ndvi: [],
  })

  const [loading, setLoading]           = useState(true)
  const [camadas, setCamadas]           = useState<Set<Camada>>(new Set(['municipios', 'alertas']))
  const [alertaSel, setAlertaSel]       = useState<AlertaGeo | null>(null)
  const [ndviSel, setNdviSel]           = useState<NdviGeo | null>(null)
  const [stats, setStats]               = useState({ municipios: 0, alertas: 0, ndvi: 0 })
  const [filtroNivel, setFiltroNivel]   = useState<'todos' | 'critico' | 'atencao'>('todos')

  const toggleCamada = (c: Camada) => {
    setCamadas(prev => {
      const next = new Set(prev)
      next.has(c) ? next.delete(c) : next.add(c)
      return next
    })
  }

  // Inicializar mapa
  useEffect(() => {
    let mounted = true

    const init = async () => {
      const L = (await import('leaflet')).default
      await import('leaflet/dist/leaflet.css')

      if (!mounted || mapRef.current) return

      const map = L.map('vigia-map', {
        center: [-15, -55],
        zoom: 4,
        zoomControl: false,
        attributionControl: false,
      })

      L.control.zoom({ position: 'bottomright' }).addTo(map)

      L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© CartoDB',
        maxZoom: 18,
      }).addTo(map)

      mapRef.current = map
      setLoading(false)
    }

    init()
    return () => {
      mounted = false
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [])

  // Camada municípios
  useEffect(() => {
    if (!mapRef.current) return
    const L = (window as any).L
    if (!L) return

    layersRef.current.municipios.forEach(m => m.remove())
    layersRef.current.municipios = []

    if (!camadas.has('municipios')) return

    fetch(`${API}/api/mapa/municipios?limit=2000`)
      .then(r => r.json())
      .then((lista: any[]) => {
        if (!mapRef.current) return
        const icone = L.divIcon({
          html: '<div style="width:4px;height:4px;background:rgba(255,255,255,0.25);border-radius:50%"></div>',
          className: '',
          iconSize: [4, 4],
        })
        const markers = lista
          .filter(m => m.lat && m.lon)
          .map(m =>
            L.marker([m.lat, m.lon], { icon: icone })
              .addTo(mapRef.current)
              .bindPopup(
                `<div style="font-family:monospace;font-size:12px"><b>${m.nome}</b><br>${m.estado || ''} · ${m.pais}</div>`
              )
          )
        layersRef.current.municipios = markers
        setStats(s => ({ ...s, municipios: lista.length }))
      })
      .catch(console.error)
  }, [camadas])

  // Camada alertas
  useEffect(() => {
    if (!mapRef.current) return
    const L = (window as any).L
    if (!L) return

    layersRef.current.alertas.forEach(m => m.remove())
    layersRef.current.alertas = []

    if (!camadas.has('alertas')) return

    const params = filtroNivel === 'todos' ? '' : `&nivel=${filtroNivel}`
    fetch(`${API}/api/mapa/alertas-geo?horas=48${params}`)
      .then(r => r.json())
      .then((lista: AlertaGeo[]) => {
        if (!mapRef.current) return
        const circles = lista.map(a => {
          const cor = COR_NIVEL[a.nivel] ?? '#60a5fa'
          const raio = a.nivel === 'critico' ? 28000 : a.nivel === 'atencao' ? 18000 : 10000

          const circle = L.circle([a.lat, a.lon], {
            radius: raio,
            color: cor,
            fillColor: cor,
            fillOpacity: 0.15,
            weight: 1.5,
            opacity: 0.6,
          }).addTo(mapRef.current)

          circle.on('click', () => {
            setNdviSel(null)
            setAlertaSel(a)
          })

          return circle
        })
        layersRef.current.alertas = circles
        setStats(s => ({ ...s, alertas: lista.length }))
      })
      .catch(console.error)
  }, [camadas, filtroNivel])

  // Camada NDVI
  useEffect(() => {
    if (!mapRef.current) return
    const L = (window as any).L
    if (!L) return

    layersRef.current.ndvi.forEach(m => m.remove())
    layersRef.current.ndvi = []

    if (!camadas.has('ndvi')) return

    fetch(`${API}/api/mapa/ndvi-geo?limit=500`)
      .then(r => r.json())
      .then((lista: NdviGeo[]) => {
        if (!mapRef.current) return
        const markers = lista
          .filter(n => n.ndvi_medio != null)
          .map(n => {
            const cor = ndviParaCor(n.ndvi_medio)
            const anomaliaStyle = n.anomalia_detectada
              ? 'border: 2px solid #f59e0b;'
              : ''

            const icon = L.divIcon({
              html: `<div style="width:10px;height:10px;background:${cor};border-radius:50%;opacity:0.8;${anomaliaStyle}"></div>`,
              className: '',
              iconSize: [10, 10],
            })

            const marker = L.marker([n.lat, n.lon], { icon })
              .addTo(mapRef.current)

            marker.on('click', () => {
              setAlertaSel(null)
              setNdviSel(n)
            })

            return marker
          })
        layersRef.current.ndvi = markers
        setStats(s => ({ ...s, ndvi: lista.length }))
      })
      .catch(console.error)
  }, [camadas])

  // Garantir que Leaflet esteja em window após init
  useEffect(() => {
    if (!mapRef.current) return
    import('leaflet').then(m => {
      ;(window as any).L = m.default
    })
  }, [loading])

  return (
    <div className="relative w-full h-full">
      <div id="vigia-map" className="w-full h-full" />

      {/* Loading */}
      {loading && (
        <div className="absolute inset-0 bg-black flex items-center justify-center z-10">
          <div className="text-white/40 text-sm tracking-widest">CARREGANDO MAPA...</div>
        </div>
      )}

      {/* HUD — topo esquerdo */}
      <div className="absolute top-4 left-4 z-10 space-y-2 max-h-[calc(100vh-5rem)] overflow-y-auto scrollbar-none">
        {/* Stats */}
        <div className="bg-black/85 border border-white/10 rounded px-4 py-3">
          <div className="text-xs text-white/25 tracking-widest mb-2">VIGÍA · MAPA SA</div>
          <div className="space-y-1 text-xs text-white/60">
            <div>{stats.municipios.toLocaleString()} municípios</div>
            {camadas.has('alertas') && <div className="text-amber-400/80">{stats.alertas} alertas ativos</div>}
            {camadas.has('ndvi')    && <div className="text-emerald-400/80">{stats.ndvi} pontos NDVI</div>}
          </div>
        </div>

        {/* Controles de camada */}
        <div className="bg-black/85 border border-white/10 rounded px-4 py-3">
          <div className="text-xs text-white/25 tracking-widest mb-2">CAMADAS</div>
          <div className="space-y-2">
            {([
              { id: 'municipios', label: 'Municípios',  cor: 'text-white/50'     },
              { id: 'alertas',    label: 'Alertas',     cor: 'text-amber-400'    },
              { id: 'ndvi',       label: 'NDVI Satélite',cor: 'text-emerald-400' },
            ] as { id: Camada; label: string; cor: string }[]).map(({ id, label, cor }) => (
              <label key={id} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={camadas.has(id)}
                  onChange={() => toggleCamada(id)}
                  className="accent-white"
                />
                <span className={`text-xs ${cor}`}>{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Filtro nível — só quando camada alertas ativa */}
        {camadas.has('alertas') && (
          <div className="bg-black/85 border border-white/10 rounded px-4 py-3">
            <div className="text-xs text-white/25 tracking-widest mb-2">NÍVEL</div>
            <div className="flex flex-col gap-1">
              {(['todos', 'critico', 'atencao'] as const).map(n => (
                <button
                  key={n}
                  onClick={() => setFiltroNivel(n)}
                  className={`text-xs text-left px-2 py-1 rounded transition-colors ${
                    filtroNivel === n
                      ? 'bg-white/15 text-white'
                      : 'text-white/35 hover:text-white/60'
                  }`}
                >
                  {n === 'todos' ? 'Todos' : n.charAt(0).toUpperCase() + n.slice(1)}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Legenda NDVI */}
        {camadas.has('ndvi') && (
          <div className="bg-black/85 border border-white/10 rounded px-4 py-3">
            <div className="text-xs text-white/25 tracking-widest mb-2">NDVI</div>
            <div className="space-y-1">
              {[
                { cor: '#8B4513', label: '< 0.1 Solo exposto' },
                { cor: '#DAA520', label: '0.2 Emergência' },
                { cor: '#9ACD32', label: '0.3 Vegetativo' },
                { cor: '#32CD32', label: '0.5 Pleno' },
                { cor: '#006400', label: '0.75+ Avançado' },
              ].map(({ cor, label }) => (
                <div key={label} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: cor }} />
                  <span className="text-xs text-white/40">{label}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Painel lateral — alerta ou NDVI */}
      {alertaSel && (
        <PainelAlerta
          alerta={alertaSel}
          onFechar={() => setAlertaSel(null)}
        />
      )}
      {ndviSel && !alertaSel && (
        <PainelNdvi
          ndvi={ndviSel}
          onFechar={() => setNdviSel(null)}
        />
      )}
    </div>
  )
}
