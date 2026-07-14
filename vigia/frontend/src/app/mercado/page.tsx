'use client'

import useSWR from 'swr'
import NavBar from '@/components/shared/NavBar'
import { mercadoApi, radarApi, type Alerta, type Cotacao } from '@/lib/api'

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

const fetcher = (url: string) => fetch(url).then(r => r.json())
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function CotacaoCard({ c }: { c: Cotacao }) {
  const sub = c.variacao_pct ?? 0
  const cor = sub > 0 ? 'text-emerald-400' : sub < 0 ? 'text-red-400' : 'text-white/40'
  const sinal = sub > 0 ? '+' : ''

  return (
    <div className="border border-white/10 rounded p-4 hover:border-white/20 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div className="text-white text-sm font-medium leading-tight">{c.praca}</div>
        <div className={`text-xs font-mono ${cor}`}>
          {sinal}{sub.toFixed(2)}%
        </div>
      </div>
      <div className="text-2xl font-light text-white tabular-nums mb-1">
        {c.preco?.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
      </div>
      <div className="flex items-center justify-between">
        <div className="text-white/35 text-xs">R$/{c.unidade}</div>
        <div className="text-white/25 text-xs">{c.fonte}</div>
      </div>
      {c.tendencia && (
        <div className="mt-2 pt-2 border-t border-white/8 text-xs text-white/30">
          Tendência: {c.tendencia}
        </div>
      )}
    </div>
  )
}

function AlertaMercadoCard({ a }: { a: Alerta }) {
  const cor = a.nivel === 'critico'
    ? 'border-red-500/30 bg-red-500/5'
    : 'border-amber-500/30 bg-amber-500/5'

  return (
    <div className={`border rounded p-4 ${cor}`}>
      <div className="text-sm font-medium text-white mb-1">{a.titulo}</div>
      <div className="text-xs text-white/55 mb-2 leading-relaxed">{a.descricao}</div>
      <div className="text-xs text-white/40">→ {a.acao_recomendada}</div>
    </div>
  )
}

export default function MercadoPage() {
  const { data: cotacoes, isLoading: lc } = useSWR(
    'mercado-cotacoes', () => mercadoApi.cotacoes(30), { refreshInterval: 120_000 }
  )
  const { data: cambio, isLoading: lca } = useSWR(
    `${API}/api/mercado/cambio`, fetcher, { refreshInterval: 300_000 }
  )
  const { data: alertas, isLoading: la } = useSWR(
    'alertas-mercado',
    () => radarApi.alertas(undefined, 50).then(al =>
      al.filter(a => a.tipo.startsWith('mercado_') || a.tipo === 'cambio_alto' || a.tipo.startsWith('preco_'))
    ),
    { refreshInterval: 60_000 }
  )

  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-16 max-w-screen-xl mx-auto px-4 md:px-6 py-8">

        {/* Header */}
        <div className="flex flex-wrap items-end justify-between gap-3 mb-8">
          <div>
            <h1 className="text-3xl font-light tracking-wide text-white">Mercado</h1>
            <p className="text-white/40 text-sm mt-1">CEPEA/ESALQ · BCB · B3</p>
          </div>
          {cambio && (
            <div className="text-right">
              <div className="text-white/30 text-xs tracking-widest mb-1">USD/BRL</div>
              <div className={`text-2xl font-light tabular-nums ${
                (cambio.usd_brl ?? 0) >= 5.5 ? 'text-amber-400' : 'text-white'
              }`}>
                {cambio.usd_brl?.toFixed(3) ?? '—'}
              </div>
            </div>
          )}
        </div>

        {/* Câmbio bar */}
        {!lca && cambio && (
          <div className="grid grid-cols-3 gap-4 mb-8">
            {[
              { label: 'USD/BRL', val: cambio.usd_brl, aviso: (cambio.usd_brl ?? 0) >= 5.5 },
              { label: 'EUR/BRL', val: cambio.eur_brl, aviso: false },
              { label: 'ARS/BRL', val: cambio.ars_brl, aviso: false },
            ].map(({ label, val, aviso }) => (
              <div key={label} className="border border-white/10 rounded p-4">
                <div className="text-white/40 text-xs mb-2 tracking-widest">{label}</div>
                <div className={`text-xl font-light tabular-nums ${aviso ? 'text-amber-400' : 'text-white'}`}>
                  {val ? val.toFixed(4) : '—'}
                </div>
                {aviso && (
                  <div className="text-amber-400/60 text-xs mt-1">Exportação favorecida</div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Alertas de mercado */}
        {(alertas?.length ?? 0) > 0 && (
          <div className="mb-8">
            <div className="text-xs text-white/30 tracking-widest mb-4">ALERTAS DE MERCADO</div>
            <div className="space-y-3">
              {alertas!.map(a => <AlertaMercadoCard key={a.id} a={a} />)}
            </div>
          </div>
        )}

        {/* Cotações */}
        <div>
          <div className="text-xs text-white/30 tracking-widest mb-4">COTAÇÕES — CEPEA/ESALQ</div>
          {lc ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array(9).fill(0).map((_, i) => <Skeleton key={i} className="h-28 rounded" />)}
            </div>
          ) : !cotacoes?.length ? (
            <div className="border border-white/10 rounded p-8 text-center">
              <div className="text-white/30 text-sm">Cotações sendo coletadas</div>
              <div className="text-white/15 text-xs mt-1">
                O scraper CEPEA coleta dados durante o seed e a cada 4h
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {cotacoes.map(c => <CotacaoCard key={c.id} c={c} />)}
            </div>
          )}
        </div>

      </main>
    </div>
  )
}
