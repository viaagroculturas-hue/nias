'use client'

import NavBar from '@/components/shared/NavBar'
import dynamic from 'next/dynamic'

const MapaInterativo = dynamic(() => import('@/components/mapa/MapaInterativo'), { ssr: false })

export default function MapaPage() {
  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-16 h-screen">
        <MapaInterativo />
      </main>
    </div>
  )
}
