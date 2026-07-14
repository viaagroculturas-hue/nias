'use client'

import { useEffect, useRef, useState } from 'react'
import RadarVivo from '@/components/radar/RadarVivo'
import TerraOverlay from '@/components/terra/TerraOverlay'
import NavBar from '@/components/shared/NavBar'
import SeedProgress from '@/components/shared/SeedProgress'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WS  = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
  .replace(/^http/, 'ws')

type BootState = 'verificando' | 'seed' | 'pronto'

function Verificando() {
  return (
    <div className="fixed inset-0 bg-black flex flex-col items-center justify-center">
      <div
        className="text-white/20 font-light tracking-[0.5em] mb-6"
        style={{ fontSize: 'clamp(1.5rem, 6vw, 3rem)' }}
      >
        VIGÍA
      </div>
      <div className="flex gap-1">
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="w-1 h-1 bg-white/20 rounded-full"
            style={{ animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite` }}
          />
        ))}
      </div>
    </div>
  )
}

export default function Home() {
  const [boot, setBoot]   = useState<BootState>('verificando')
  const [terra, setTerra] = useState<any>(null)
  const wsRef = useRef<WebSocket | null>(null)

  // 1. Checar seed
  useEffect(() => {
    const controller = new AbortController()
    fetch(`${API}/api/seed/status`, { signal: controller.signal })
      .then(r => r.json())
      .then(d => {
        if (d.concluido) {
          setBoot('pronto')
        } else {
          if (!d.iniciado) {
            fetch(`${API}/api/seed/iniciar`, { method: 'POST' }).catch(() => {})
          }
          setBoot('seed')
        }
      })
      .catch(() => setBoot('pronto'))  // backend indisponível → mostrar UI mesmo assim

    return () => controller.abort()
  }, [])

  // 2. WebSocket TERRA
  useEffect(() => {
    if (boot !== 'pronto') return
    let cancelado = false

    const conectar = () => {
      if (cancelado) return
      try {
        const ws = new WebSocket(`${WS}/api/radar/ws`)
        wsRef.current = ws
        ws.onmessage = e => {
          try {
            const msg = JSON.parse(e.data)
            if (msg.type === 'TERRA') setTerra(msg.data)
          } catch {}
        }
        ws.onclose  = () => { if (!cancelado) setTimeout(conectar, 5_000) }
        ws.onerror  = () => ws.close()
      } catch {}
    }

    conectar()
    return () => {
      cancelado = true
      wsRef.current?.close()
    }
  }, [boot])

  if (boot === 'verificando') return <Verificando />
  if (boot === 'seed')        return <SeedProgress onConcluido={() => setBoot('pronto')} />

  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-14 md:pt-16">
        <RadarVivo />
      </main>
      {terra && (
        <TerraOverlay
          terra={terra}
          onReconhecer={() => setTerra(null)}
        />
      )}
    </div>
  )
}
