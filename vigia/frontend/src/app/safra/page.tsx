'use client'

import useSWR from 'swr'
import NavBar from '@/components/shared/NavBar'
import { radarApi, type Alerta } from '@/lib/api'
import EmptyState from '@/components/shared/EmptyState'

const fetcher = (url: string) => fetch(url).then(r => r.json())
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

const FASE_COR: Record<string, string> = {
  plantio:       'text-yellow-400',
  vegetativo:    'text-emerald-400',
  florescimento: 'text-pink-400',
  granacao:      'text-orange-400',
  colheita:      'text-amber-400',
  entressafra:   'text-white/30',
}

const CATEGORIAS: Record<string, string[]> = {
  'Grãos':     ['Soja', 'Milho', 'Trigo', 'Arroz', 'Feijão'],
  'Café':      ['Café Arábica'],
  'Cana':      ['Cana-de-açúcar'],
  'Frutas':    ['Banana', 'Manga', 'Laranja', 'Uva', 'Açaí', 'Abacate'],
  'Olerícolas':['Tomate', 'Alho', 'Cebola', 'Batata'],
  'Outros':    ['Mandioca', 'Algodão', 'Quinoa'],
}

function ProducaoAlertaCard({ a }: { a: Alerta }) {
  return (
    <div className="border border-amber-500/30 bg-amber-500/5 rounded p-4">
      <div className="text-white text-sm font-medium mb-1">{a.titulo}</div>
      <div className="text-white/55 text-xs leading-relaxed">{a.descricao}</div>
      {a.acao_recomendada && (
        <div className="text-white/40 text-xs mt-2">→ {a.acao_recomendada}</div>
      )}
    </div>
  )
}

export default function SafraPage() {
  const { data: safras, isLoading: ls } = useSWR(`${API}/api/safra/`, fetcher)
  const { data: culturas, isLoading: lc } = useSWR(`${API}/api/safra/culturas`, fetcher)
  const { data: alertas } = useSWR(
    'alertas-producao',
    () => radarApi.alertas(undefined, 50).then(al =>
      al.filter(a => a.tipo.startsWith('producao_') || a.tipo.startsWith('viveiro_'))
    ),
    { refreshInterval: 60_000 }
  )

  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-16 max-w-screen-xl mx-auto px-4 md:px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-light tracking-wide text-white">Safras</h1>
          <p className="text-white/40 text-sm mt-1">
            Ciclos produtivos · 85 culturas · América do Sul
          </p>
        </div>

        {/* Alertas de produção */}
        {(alertas?.length ?? 0) > 0 && (
          <div className="mb-8">
            <div className="text-xs text-white/30 tracking-widest mb-4">ALERTAS DE PRODUÇÃO</div>
            <div className="space-y-3">
              {alertas!.map(a => <ProducaoAlertaCard key={a.id} a={a} />)}
            </div>
          </div>
        )}

        {/* Culturas por categoria — sempre visível */}
        <div className="mb-10">
          <div className="text-xs text-white/30 tracking-widest mb-4">CULTURAS MONITORADAS — 85 TOTAL</div>
          {lc ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {Array(18).fill(0).map((_, i) => <Skeleton key={i} className="h-10 rounded" />)}
            </div>
          ) : culturas?.length ? (
            <div className="space-y-6">
              {Object.entries(CATEGORIAS).map(([cat, nomes]) => {
                const lista = culturas.filter((c: any) =>
                  nomes.some(n => c.nome?.toLowerCase().includes(n.toLowerCase()))
                )
                if (!lista.length) return null
                return (
                  <div key={cat}>
                    <div className="text-xs text-white/20 tracking-widest mb-2">{cat.toUpperCase()}</div>
                    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
                      {lista.map((c: any) => (
                        <div key={c.id} className="border border-white/8 rounded p-3">
                          <div className="text-white text-xs font-medium">{c.nome}</div>
                          {c.fase_atual && (
                            <div className={`text-xs mt-0.5 capitalize ${FASE_COR[c.fase_atual] ?? 'text-white/40'}`}>
                              {c.fase_atual}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
              {Object.values(CATEGORIAS).flat().map(nome => (
                <div key={nome} className="border border-white/8 rounded p-3">
                  <div className="text-white text-xs">{nome}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Safras ativas do DB */}
        <div>
          <div className="text-xs text-white/30 tracking-widest mb-4">SAFRAS ATIVAS</div>
          {ls ? (
            <div className="space-y-2">
              {Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-16 rounded" />)}
            </div>
          ) : !safras?.length ? (
            <EmptyState
              titulo="Safras serão cadastradas após integração CONAB"
              subtitulo="As culturas monitoradas acima são sempre exibidas independente do status do banco"
            />
          ) : (
            <div className="space-y-3">
              {safras.map((s: any) => (
                <div key={s.id} className="border border-white/10 rounded p-4 flex items-center gap-6">
                  <div className="text-white text-sm w-16">{s.ano_safra}</div>
                  <div className="text-white/60 text-sm flex-1">{s.cultura_nome ?? s.cultura_id}</div>
                  {s.fase_atual && (
                    <div className={`text-xs capitalize ${FASE_COR[s.fase_atual] ?? 'text-white/40'}`}>
                      {s.fase_atual}
                    </div>
                  )}
                  {s.area_plantada_ha && (
                    <div className="text-white/40 text-xs tabular-nums">
                      {Number(s.area_plantada_ha).toLocaleString('pt-BR')} ha
                    </div>
                  )}
                  <div className="text-white/25 text-xs">{s.status}</div>
                </div>
              ))}
            </div>
          )}
        </div>

      </main>
    </div>
  )
}
