'use client'

import useSWR from 'swr'
import NavBar from '@/components/shared/NavBar'
import { demandaApi, type FatorDemanda } from '@/lib/api'
import EmptyState from '@/components/shared/EmptyState'

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

function ImpactoBar({ pct, direcao }: { pct: number; direcao: string }) {
  const cor = direcao === 'reducao' ? 'bg-red-500' : 'bg-emerald-500'
  const label = direcao === 'reducao' ? `−${pct}%` : `+${pct}%`
  const labelCor = direcao === 'reducao' ? 'text-red-400' : 'text-emerald-400'

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1 bg-white/10 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${cor} opacity-70`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      <span className={`text-xs font-mono w-12 text-right ${labelCor}`}>{label}</span>
    </div>
  )
}

function FatorCard({ f }: { f: FatorDemanda }) {
  const borderCor = f.impacto_direcao === 'reducao'
    ? 'border-red-500/20 hover:border-red-500/35'
    : 'border-emerald-500/20 hover:border-emerald-500/35'

  return (
    <div className={`border rounded p-5 transition-colors ${borderCor}`}>
      {/* Nome + badge */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="text-white text-sm font-medium leading-snug">{f.nome}</div>
        <span className={`text-xs flex-shrink-0 mt-0.5 ${
          f.tipo === 'saude' ? 'text-purple-400' :
          f.tipo === 'macro' ? 'text-blue-400' :
          f.tipo === 'social' ? 'text-cyan-400' :
          'text-white/40'
        }`}>{f.tipo}</span>
      </div>

      {/* Barra de impacto */}
      <ImpactoBar pct={f.impacto_pct} direcao={f.impacto_direcao} />

      {/* Culturas afetadas */}
      {f.culturas_afetadas?.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-3 mb-2">
          {f.culturas_afetadas.slice(0, 4).map(c => (
            <span key={c} className="text-xs text-white/40 border border-white/10 px-1.5 py-0.5 rounded">
              {c}
            </span>
          ))}
          {f.culturas_afetadas.length > 4 && (
            <span className="text-xs text-white/25">+{f.culturas_afetadas.length - 4}</span>
          )}
        </div>
      )}

      {/* Rodapé */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-white/8">
        <span className="text-white/25 text-xs">{f.fonte_dado}</span>
        <span className="text-white/25 text-xs">{f.confianca_pct}% conf.</span>
      </div>

      {/* Período */}
      {(f.periodo_inicio || f.periodo_fim) && (
        <div className="text-white/20 text-xs mt-1">
          {f.periodo_inicio?.slice(0, 10)} — {f.periodo_fim?.slice(0, 10) ?? 'contínuo'}
        </div>
      )}
    </div>
  )
}

export default function DemandaPage() {
  const { data: fatores, isLoading } = useSWR('demanda-fatores', demandaApi.fatores, {
    refreshInterval: 3_600_000,
  })

  const reducao  = fatores?.filter(f => f.impacto_direcao === 'reducao')  ?? []
  const aumento  = fatores?.filter(f => f.impacto_direcao === 'aumento')  ?? []

  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-16 max-w-screen-xl mx-auto px-4 md:px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-light tracking-wide text-white">Fatores de Demanda</h1>
          <p className="text-white/40 text-sm mt-1">
            Forças estruturais que moldam o consumo — GLP-1, câmbio, eventos, macro
          </p>
        </div>

        {/* Resumo */}
        {!isLoading && fatores?.length ? (
          <div className="grid grid-cols-2 gap-4 mb-8">
            <div className="border border-red-500/20 rounded p-4">
              <div className="text-xs text-white/30 tracking-widest mb-2">REDUZEM DEMANDA</div>
              <div className="text-3xl font-light text-red-400">{reducao.length}</div>
              <div className="text-xs text-white/30 mt-1">fatores ativos</div>
            </div>
            <div className="border border-emerald-500/20 rounded p-4">
              <div className="text-xs text-white/30 tracking-widest mb-2">AUMENTAM DEMANDA</div>
              <div className="text-3xl font-light text-emerald-400">{aumento.length}</div>
              <div className="text-xs text-white/30 mt-1">fatores ativos</div>
            </div>
          </div>
        ) : null}

        {/* Grid de fatores */}
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array(12).fill(0).map((_, i) => <Skeleton key={i} className="h-48 rounded" />)}
          </div>
        ) : !fatores?.length ? (
          <EmptyState
            titulo="Fatores de demanda não carregados"
            subtitulo="Seed Etapa 7 popula os 12 fatores automaticamente no primeiro boot"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {fatores.map(f => <FatorCard key={f.id} f={f} />)}
          </div>
        )}

      </main>
    </div>
  )
}
