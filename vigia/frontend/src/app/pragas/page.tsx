'use client'

import useSWR from 'swr'
import NavBar from '@/components/shared/NavBar'
import { radarApi, type Alerta } from '@/lib/api'
import EmptyState from '@/components/shared/EmptyState'

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

const fetcher = (url: string) => fetch(url).then(r => r.json())
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const REGRAS_PRAGA = [
  { praga: 'Ferrugem Asiática',  cultura: 'Soja',        nivel: 'critico', perda: 80, periodo: 'Out–Jan' },
  { praga: 'Brusone do Trigo',   cultura: 'Trigo',       nivel: 'critico', perda: 70, periodo: 'Abr–Jun' },
  { praga: 'Lagarta-do-cartucho',cultura: 'Milho',       nivel: 'atencao', perda: 34, periodo: 'Nov–Mar' },
  { praga: 'Mal-do-Panamá (TR4)',cultura: 'Banana',      nivel: 'critico', perda: 100,periodo: 'ano todo' },
  { praga: 'Requeima',           cultura: 'Tomate',      nivel: 'critico', perda: 90, periodo: 'Mar–Jul' },
  { praga: 'Cigarrinha',         cultura: 'Cana',        nivel: 'atencao', perda: 25, periodo: 'Out–Mar' },
  { praga: 'Broca-do-café (CBB)',cultura: 'Café',        nivel: 'atencao', perda: 35, periodo: 'Mai–Set' },
]

function PragaAlertaCard({ a }: { a: Alerta }) {
  const cor = a.nivel === 'critico'
    ? 'border-red-500/40 bg-red-500/5'
    : 'border-amber-500/30 bg-amber-500/5'

  return (
    <div className={`border rounded p-4 ${cor}`}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`text-xs px-2 py-0.5 rounded border ${
              a.nivel === 'critico'
                ? 'border-red-500/50 text-red-400'
                : 'border-amber-500/50 text-amber-400'
            }`}>{a.nivel.toUpperCase()}</span>
          </div>
          <div className="text-white text-sm font-medium mb-1">{a.titulo}</div>
          <div className="text-white/55 text-xs leading-relaxed mb-2">{a.descricao}</div>
          {a.confianca_pct > 0 && (
            <div className="flex items-center gap-4 text-xs text-white/30 mb-2">
              <span>Confiança {a.confianca_pct.toFixed(0)}%</span>
              <span>{a.fontes?.join(' · ')}</span>
            </div>
          )}
          {a.acao_recomendada && (
            <div className="pt-2 border-t border-white/10 text-xs text-white/60">
              → {a.acao_recomendada}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function PragasPage() {
  const { data: pragas, isLoading: lp } = useSWR(`${API}/api/pragas/`, fetcher)
  const { data: alertas, isLoading: la } = useSWR(
    'alertas-pragas',
    () => radarApi.alertas(undefined, 50).then(al =>
      al.filter(a => a.tipo.startsWith('praga_'))
    ),
    { refreshInterval: 60_000 }
  )

  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-16 max-w-screen-xl mx-auto px-4 md:px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-light tracking-wide text-white">Pragas e Doenças</h1>
          <p className="text-white/40 text-sm mt-1">Monitoramento fitossanitário — detecção por condições climáticas</p>
        </div>

        {/* Alertas ativos do agente fitossanitário */}
        <div className="mb-10">
          <div className="text-xs text-white/30 tracking-widest mb-4">ALERTAS FITOSSANITÁRIOS ATIVOS</div>
          {la ? (
            <div className="space-y-3">
              {Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-28 rounded" />)}
            </div>
          ) : !alertas?.length ? (
            <EmptyState
              titulo="Nenhum alerta fitossanitário ativo"
              subtitulo="O agente cruza eventos climáticos com condições favoráveis a cada 2h"
            />
          ) : (
            <div className="space-y-3">
              {alertas.map(a => <PragaAlertaCard key={a.id} a={a} />)}
            </div>
          )}
        </div>

        {/* Mapa de risco por cultura — sempre visível */}
        <div className="mb-10">
          <div className="text-xs text-white/30 tracking-widest mb-4">RISCO POR CULTURA — REGRAS ATIVAS</div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left text-white/30 text-xs tracking-widest py-3 pr-6 font-normal">PRAGA/DOENÇA</th>
                  <th className="text-left text-white/30 text-xs tracking-widest py-3 pr-6 font-normal">CULTURA</th>
                  <th className="text-left text-white/30 text-xs tracking-widest py-3 pr-6 font-normal">RISCO</th>
                  <th className="text-right text-white/30 text-xs tracking-widest py-3 pr-6 font-normal">PERDA MÁXIMA</th>
                  <th className="text-right text-white/30 text-xs tracking-widest py-3 font-normal">PERÍODO</th>
                </tr>
              </thead>
              <tbody>
                {REGRAS_PRAGA.map((r, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/2 transition-colors">
                    <td className="py-3 pr-6 text-white">{r.praga}</td>
                    <td className="py-3 pr-6 text-white/60">{r.cultura}</td>
                    <td className="py-3 pr-6">
                      <span className={`text-xs px-2 py-0.5 rounded border ${
                        r.nivel === 'critico'
                          ? 'border-red-500/40 text-red-400'
                          : 'border-amber-500/40 text-amber-400'
                      }`}>{r.nivel.toUpperCase()}</span>
                    </td>
                    <td className="py-3 pr-6 text-right">
                      <span className={r.perda >= 80 ? 'text-red-400' : r.perda >= 40 ? 'text-amber-400' : 'text-white/60'}>
                        {r.perda}%
                      </span>
                    </td>
                    <td className="py-3 text-right text-white/40 text-xs">{r.periodo}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Catálogo do DB */}
        {lp ? null : pragas?.length ? (
          <div>
            <div className="text-xs text-white/30 tracking-widest mb-4">CATÁLOGO FITOSSANITÁRIO — BD</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {pragas.map((p: any) => (
                <div key={p.id} className="border border-white/8 rounded p-3">
                  <div className="text-white text-sm">{p.nome_comum}</div>
                  <div className="text-white/35 text-xs italic">{p.nome_cientifico}</div>
                  {p.perda_potencial_pct && (
                    <div className="text-red-400/70 text-xs mt-1">Perda potencial: {p.perda_potencial_pct}%</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ) : null}

      </main>
    </div>
  )
}
