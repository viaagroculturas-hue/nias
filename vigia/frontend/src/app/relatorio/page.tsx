'use client'

import { useState } from 'react'
import useSWR from 'swr'
import NavBar from '@/components/shared/NavBar'
import { relatorioApi, inteligenciaApi } from '@/lib/api'

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

export default function RelatorioPage() {
  const [executando, setExecutando] = useState(false)
  const [triggerMsg, setTriggerMsg] = useState('')

  const { data, isLoading, mutate } = useSWR('relatorio-hoje', relatorioApi.hoje, {
    refreshInterval: 60_000,
  })
  const { data: historico } = useSWR(
    'relatorio-historico', () => relatorioApi.historico(10), { refreshInterval: 300_000 }
  )

  const triggerAgentes = async () => {
    setExecutando(true)
    setTriggerMsg('')
    try {
      const res = await inteligenciaApi.executarAgentes()
      const total = Object.values(res.resultado as Record<string, number>)
        .reduce((a, b) => a + b, 0)
      setTriggerMsg(`Ciclo concluído — ${total} alertas processados`)
      mutate()
    } catch {
      setTriggerMsg('Erro ao executar agentes')
    } finally {
      setExecutando(false)
    }
  }

  return (
    <div className="min-h-screen bg-black">
      <NavBar />
      <main className="pt-16 max-w-3xl mx-auto px-4 md:px-6 py-8">

        {/* Header */}
        <div className="flex flex-wrap items-end justify-between gap-3 mb-8">
          <div>
            <h1 className="text-3xl font-light tracking-wide text-white">Relatório 05h30</h1>
            <p className="text-white/40 text-sm mt-1">Gerado antes do mercado abrir — sempre 3 ações</p>
          </div>
          <button
            onClick={triggerAgentes}
            disabled={executando}
            className="text-xs text-white/30 border border-white/10 px-4 py-2 rounded hover:border-white/25 hover:text-white/60 transition-colors disabled:opacity-40 flex-shrink-0"
          >
            {executando ? 'Executando...' : 'Rodar agentes agora'}
          </button>
        </div>

        {triggerMsg && (
          <div className="border border-white/10 rounded p-3 mb-6 text-white/60 text-xs">
            {triggerMsg}
          </div>
        )}

        {/* Relatório de hoje */}
        {isLoading ? (
          <div className="space-y-4">
            <Skeleton className="h-6 rounded w-48" />
            <Skeleton className="h-32 rounded" />
            <Skeleton className="h-24 rounded" />
          </div>
        ) : !data?.disponivel ? (
          <div className="border border-white/10 rounded p-8 text-center mb-8">
            <div className="text-white/40 text-sm mb-2">Relatório não disponível para hoje</div>
            <div className="text-white/20 text-xs">
              Gerado automaticamente às 05h30 (Brasília) via Celery Beat
            </div>
          </div>
        ) : (
          <div className="space-y-8 mb-12">
            {/* Meta */}
            <div className="flex items-center gap-6 text-xs text-white/30 tracking-widest">
              <span>{data.data_referencia}</span>
              {data.municipios_monitorados && <span>{data.municipios_monitorados.toLocaleString()} municípios</span>}
              {data.alertas_gerados != null && <span>{data.alertas_gerados} alertas</span>}
              {data.enviado_whatsapp && <span className="text-emerald-400">✓ WhatsApp enviado</span>}
              <span className="text-white/15">
                {data.gerado_em
                  ? new Date(data.gerado_em).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
                  : ''}
              </span>
            </div>

            {/* Resumo */}
            <div>
              <div className="text-xs text-white/30 tracking-widest mb-3">RESUMO EXECUTIVO</div>
              <p className="text-white/80 text-sm leading-relaxed">{data.resumo_executivo}</p>
            </div>

            {/* 3 Ações */}
            {data.acoes_do_dia?.length > 0 && (
              <div>
                <div className="text-xs text-white/30 tracking-widest mb-3">3 AÇÕES DO DIA</div>
                <div className="space-y-3">
                  {data.acoes_do_dia.map((acao: any, i: number) => (
                    <div key={i} className="border border-white/10 rounded p-4">
                      <div className="flex items-start gap-3">
                        <span className="text-white/20 text-xl font-light w-6 flex-shrink-0">{i + 1}</span>
                        <div>
                          <div className="text-white font-medium text-sm">{acao.titulo}</div>
                          <div className="text-white/50 text-xs mt-1 leading-relaxed">{acao.acao}</div>
                          <div className="flex gap-4 mt-2 text-xs text-white/25">
                            <span>Prazo: {acao.prazo}</span>
                            {acao.origem && <span>{acao.origem.replace('_', ' ')}</span>}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Alertas críticos */}
            {(data.alertas_criticos as any[])?.length > 0 && (
              <div>
                <div className="text-xs text-white/30 tracking-widest mb-3">ALERTAS CRÍTICOS</div>
                <div className="space-y-3">
                  {(data.alertas_criticos as any[]).map((a, i) => (
                    <div key={i} className="border border-red-500/30 rounded p-4 bg-red-500/5">
                      <div className="text-sm font-medium text-red-400 mb-1">{a.titulo}</div>
                      <div className="text-xs text-white/60 leading-relaxed">{a.descricao}</div>
                      {a.acao_recomendada && (
                        <div className="text-xs text-white/45 mt-2">→ {a.acao_recomendada}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Mercado snapshot */}
            {(data.mercado_snapshot as any[])?.length > 0 && (
              <div>
                <div className="text-xs text-white/30 tracking-widest mb-3">MERCADO — SNAPSHOT</div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {(data.mercado_snapshot as any[]).slice(0, 6).map((c, i) => (
                    <div key={i} className="border border-white/8 rounded p-3">
                      <div className="text-white/50 text-xs mb-1">{c.praca}</div>
                      <div className="text-white text-sm tabular-nums">
                        R$ {Number(c.preco).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}
                      </div>
                      {c.variacao != null && (
                        <div className={`text-xs ${c.variacao >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          {c.variacao >= 0 ? '+' : ''}{Number(c.variacao).toFixed(2)}%
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ENSO */}
            {data.enso_snapshot && Object.keys(data.enso_snapshot).length > 0 && (
              <div>
                <div className="text-xs text-white/30 tracking-widest mb-3">ENSO</div>
                <div className="border border-white/10 rounded p-4 flex gap-8 text-sm">
                  <div>
                    <div className="text-white/30 text-xs mb-1">Tipo</div>
                    <div className="text-white">{(data.enso_snapshot as any).tipo || '—'}</div>
                  </div>
                  <div>
                    <div className="text-white/30 text-xs mb-1">ONI</div>
                    <div className="text-white tabular-nums">
                      {(data.enso_snapshot as any).oni != null
                        ? ((data.enso_snapshot as any).oni > 0 ? '+' : '') + Number((data.enso_snapshot as any).oni).toFixed(1)
                        : '—'}
                    </div>
                  </div>
                  <div>
                    <div className="text-white/30 text-xs mb-1">Probabilidade</div>
                    <div className="text-white">{(data.enso_snapshot as any).probabilidade ?? '—'}%</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Histórico */}
        {historico?.length ? (
          <div>
            <div className="text-xs text-white/30 tracking-widest mb-4">HISTÓRICO — ÚLTIMOS 10 DIAS</div>
            <div className="space-y-2">
              {historico.map((r: any) => (
                <div key={r.id} className="border border-white/8 rounded p-3 flex items-center gap-6">
                  <span className="text-white/50 text-xs tabular-nums w-24 flex-shrink-0">
                    {r.data_referencia}
                  </span>
                  <span className="text-white/30 text-xs">
                    {r.alertas_criticos} críticos
                  </span>
                  <span className="text-white/20 text-xs">
                    {r.municipios_monitorados?.toLocaleString()} municípios
                  </span>
                  <span className="text-white/15 text-xs ml-auto">
                    {r.gerado_em ? new Date(r.gerado_em).toLocaleTimeString('pt-BR', {
                      hour: '2-digit', minute: '2-digit',
                    }) : ''}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ) : null}

      </main>
    </div>
  )
}
