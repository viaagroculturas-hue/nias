'use client'

import useSWR from 'swr'
import NavBar from '@/components/shared/NavBar'
import { climaApi, radarApi, type Alerta } from '@/lib/api'
import EmptyState from '@/components/shared/EmptyState'

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

const ENSO_COR: Record<string, string> = {
  el_nino:        'text-orange-400 border-orange-500/30 bg-orange-500/5',
  la_nina:        'text-blue-400 border-blue-500/30 bg-blue-500/5',
  neutro:         'text-white/60 border-white/10',
  transicao:      'text-yellow-400 border-yellow-500/30 bg-yellow-500/5',
}

function AlertaClimaticoCard({ a }: { a: Alerta }) {
  const cor = a.nivel === 'critico'
    ? 'border-red-500/40 bg-red-500/5 text-red-400'
    : a.nivel === 'atencao'
    ? 'border-amber-500/30 bg-amber-500/5 text-amber-400'
    : 'border-blue-500/20 bg-blue-500/5 text-blue-400'

  return (
    <div className={`border rounded p-4 ${cor.split(' ').slice(0,2).join(' ')}`}>
      <div className="flex items-start gap-3">
        <div className={`text-xs px-2 py-0.5 rounded border flex-shrink-0 mt-0.5 ${cor}`}>
          {a.nivel.toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-white text-sm font-medium mb-1">{a.titulo}</div>
          <div className="text-white/55 text-xs leading-relaxed mb-2">{a.descricao}</div>
          <div className="flex items-center gap-4 text-xs text-white/30">
            <span>Confiança {a.confianca_pct.toFixed(0)}%</span>
            {a.fontes?.length > 0 && <span>{a.fontes.join(' · ')}</span>}
          </div>
          {a.acao_recomendada && (
            <div className="mt-2 pt-2 border-t border-white/10 text-xs text-white/55">
              → {a.acao_recomendada}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function ClimaPage() {
  const { data: enso, isLoading: le } = useSWR('enso', climaApi.enso, { refreshInterval: 3_600_000 })
  const { data: eventos, isLoading: lev } = useSWR('eventos-clima', () => climaApi.eventos(30), { refreshInterval: 120_000 })
  const { data: alertas, isLoading: la } = useSWR(
    'alertas-clima',
    () => radarApi.alertas(undefined, 50).then(al =>
      al.filter(a =>
        ['chuva_intensa','chuva_moderada','geada','calor_extremo','vento_forte']
          .some(t => a.tipo.includes(t)) ||
        a.tipo.startsWith('enso_')
      )
    ),
    { refreshInterval: 60_000 }
  )

  const ensoTipo = enso?.tipo_enso || 'neutro'
  const ensoCor = ENSO_COR[ensoTipo] || ENSO_COR.neutro

  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-16 max-w-screen-xl mx-auto px-4 md:px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-light tracking-wide text-white">Clima</h1>
          <p className="text-white/40 text-sm mt-1">INMET · NOAA · CPTEC · SMN · DMC · SENAMHI</p>
        </div>

        {/* ENSO */}
        <div className="mb-8">
          <div className="text-xs text-white/30 tracking-widest mb-4">ENSO — PACÍFICO EQUATORIAL</div>
          {le ? (
            <Skeleton className="h-40 rounded" />
          ) : !enso?.disponivel ? (
            <div className="border border-white/10 rounded p-6 text-white/30 text-sm text-center">
              ENSO não disponível — verificar conexão NOAA
            </div>
          ) : (
            <div className={`border rounded p-6 ${ensoCor.split(' ').filter(c => c.startsWith('border') || c.startsWith('bg')).join(' ')}`}>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6">
                <div>
                  <div className="text-white/40 text-xs mb-1 tracking-widest">FASE</div>
                  <div className={`text-xl font-light capitalize ${ensoCor.split(' ')[0]}`}>
                    {ensoTipo.replace('_', ' ')}
                  </div>
                </div>
                <div>
                  <div className="text-white/40 text-xs mb-1 tracking-widest">ÍNDICE ONI</div>
                  <div className="text-xl font-light text-white tabular-nums">
                    {enso.oni_index != null ? (enso.oni_index > 0 ? '+' : '') + enso.oni_index.toFixed(1) : '—'}
                  </div>
                </div>
                <div>
                  <div className="text-white/40 text-xs mb-1 tracking-widest">PROBABILIDADE</div>
                  <div className="text-xl font-light text-white">{enso.probabilidade_pct ?? '—'}%</div>
                </div>
                <div>
                  <div className="text-white/40 text-xs mb-1 tracking-widest">NÍVEL ALERTA</div>
                  <div className={`text-xl font-light capitalize ${
                    enso.nivel_alerta === 'critico' ? 'text-red-400' :
                    enso.nivel_alerta === 'atencao' ? 'text-amber-400' : 'text-white/60'
                  }`}>{enso.nivel_alerta ?? 'monitorar'}</div>
                </div>
              </div>

              {(enso.culturas_em_risco?.length ?? 0) > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <div className="text-white/30 text-xs tracking-widest mb-2">CULTURAS EM RISCO</div>
                    <div className="flex flex-wrap gap-2">
                      {enso.culturas_em_risco!.map(c => (
                        <span key={c} className="text-xs border border-red-500/30 bg-red-500/5 text-red-300 px-2 py-1 rounded">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                  {(enso.culturas_beneficiadas?.length ?? 0) > 0 && (
                    <div>
                      <div className="text-white/30 text-xs tracking-widest mb-2">CULTURAS BENEFICIADAS</div>
                      <div className="flex flex-wrap gap-2">
                        {enso.culturas_beneficiadas!.map(c => (
                          <span key={c} className="text-xs border border-emerald-500/30 bg-emerald-500/5 text-emerald-300 px-2 py-1 rounded">
                            {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {(enso.recomendacoes?.length ?? 0) > 0 && (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="text-white/30 text-xs tracking-widest mb-2">RECOMENDAÇÕES NOAA</div>
                  <ul className="space-y-1">
                    {enso.recomendacoes!.map((r, i) => (
                      <li key={i} className="text-white/60 text-xs">→ {r}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Alertas climáticos gerados pelos agentes */}
        <div className="mb-8">
          <div className="text-xs text-white/30 tracking-widest mb-4">ALERTAS CLIMÁTICOS ATIVOS</div>
          {la ? (
            <div className="space-y-3">
              {Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-24 rounded" />)}
            </div>
          ) : !alertas?.length ? (
            <EmptyState
              titulo="Nenhum alerta climático ativo"
              subtitulo="O agente monitora INMET e NOAA a cada 2h — você será notificado ao detectar algo relevante"
            />
          ) : (
            <div className="space-y-3">
              {alertas.map(a => <AlertaClimaticoCard key={a.id} a={a} />)}
            </div>
          )}
        </div>

        {/* Eventos brutos */}
        <div>
          <div className="text-xs text-white/30 tracking-widest mb-4">EVENTOS RECENTES — INMET</div>
          {lev ? (
            <div className="space-y-2">
              {Array(5).fill(0).map((_, i) => <Skeleton key={i} className="h-14 rounded" />)}
            </div>
          ) : !eventos?.length ? (
            <EmptyState
              titulo="Eventos sendo coletados"
              subtitulo="O scraper INMET coleta dados a cada 6h durante os ciclos do Celery Beat"
            />
          ) : (
            <div className="space-y-2">
              {eventos.map(e => (
                <div key={e.id} className="border border-white/8 rounded p-3 flex items-center gap-4">
                  <div className="text-white/60 text-xs capitalize w-28 flex-shrink-0">{e.tipo?.replace('_', ' ')}</div>
                  <div className="text-white/30 text-xs flex-shrink-0">{e.intensidade}</div>
                  {e.precipitacao_mm != null && (
                    <div className="text-white/50 text-xs">{e.precipitacao_mm}mm</div>
                  )}
                  {e.temperatura_max != null && (
                    <div className="text-white/50 text-xs">{e.temperatura_max}°C</div>
                  )}
                  <div className="text-white/20 text-xs ml-auto">{e.fonte}</div>
                </div>
              ))}
            </div>
          )}
        </div>

      </main>
    </div>
  )
}
