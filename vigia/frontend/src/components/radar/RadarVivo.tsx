'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { radarApi, type Alerta, type RadarResumo } from '@/lib/api'
import EmptyState from '@/components/shared/EmptyState'

function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

function tempoRelativo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const min = Math.floor(diff / 60_000)
  if (min < 1)   return 'agora'
  if (min < 60)  return `${min}min`
  const h = Math.floor(min / 60)
  if (h < 24)    return `${h}h`
  return `${Math.floor(h / 24)}d`
}

const COR_NIVEL = {
  critico: { borda: 'border-red-500/40 bg-red-500/5',   dot: 'bg-red-500',   badge: 'border-red-500/50 text-red-400' },
  atencao: { borda: 'border-amber-500/40 bg-amber-500/5', dot: 'bg-amber-400', badge: 'border-amber-500/50 text-amber-400' },
  info:    { borda: 'border-blue-500/20 bg-blue-500/5',  dot: 'bg-blue-400',  badge: 'border-blue-500/40 text-blue-400' },
  terra:   { borda: 'border-white bg-white/5',           dot: 'bg-white',     badge: 'border-white/50 text-white' },
}

type NivelFiltro = 'todos' | 'critico' | 'atencao' | 'info'

function AlertaCard({ alerta }: { alerta: Alerta }) {
  const cor = COR_NIVEL[alerta.nivel] ?? COR_NIVEL.info

  return (
    <div className={`border rounded p-4 ${cor.borda}`}>
      <div className="flex items-start gap-3">
        <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${cor.dot}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2 mb-1">
            <div className="text-sm font-medium text-white leading-snug">{alerta.titulo}</div>
            <span className="text-white/25 text-xs flex-shrink-0 tabular-nums">
              {alerta.created_at ? tempoRelativo(alerta.created_at) : ''}
            </span>
          </div>
          {alerta.descricao && (
            <div className="text-xs text-white/55 mb-2 line-clamp-2 leading-relaxed">
              {alerta.descricao}
            </div>
          )}
          <div className="flex items-center gap-4 text-xs text-white/30">
            <span className={`border px-1.5 py-0.5 rounded text-xs ${cor.badge}`}>
              {alerta.nivel.toUpperCase()}
            </span>
            <span>Confiança {alerta.confianca_pct.toFixed(0)}%</span>
            {alerta.impacto_financeiro > 0 && (
              <span>
                R$ {alerta.impacto_financeiro.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}
              </span>
            )}
            {alerta.fontes?.length > 0 && (
              <span className="hidden md:inline">{alerta.fontes.join(' · ')}</span>
            )}
          </div>
          {alerta.acao_recomendada && (
            <div className="mt-2 pt-2 border-t border-white/8 text-xs text-white/55">
              → {alerta.acao_recomendada}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ContadorAlerta({ count, nivel, rotulo }: { count: number; nivel: string; rotulo: string }) {
  const cores: Record<string, string> = {
    critico: 'text-red-400 border-red-500/30',
    atencao: 'text-amber-400 border-amber-500/30',
    info:    'text-blue-400 border-blue-500/30',
  }
  return (
    <div className={`border rounded p-3 md:p-5 ${cores[nivel]}`}>
      <div className="text-3xl md:text-4xl font-light mb-1">{count}</div>
      <div className="text-xs text-white/40 tracking-widest">{rotulo}</div>
    </div>
  )
}

export default function RadarVivo() {
  const [filtro, setFiltro] = useState<NivelFiltro>('todos')

  const { data: radar, isLoading: lr } = useSWR(
    'radar-resumo', radarApi.resumo, { refreshInterval: 30_000 }
  )
  const { data: todos, isLoading: la } = useSWR(
    'radar-alertas', () => radarApi.alertas(undefined, 50), { refreshInterval: 30_000 }
  )

  const alertas = filtro === 'todos' ? todos : todos?.filter(a => a.nivel === filtro)

  return (
    <div className="max-w-screen-xl mx-auto px-4 md:px-6 py-8">

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-2 mb-8">
        <div>
          <h1 className="text-3xl font-light tracking-wide">Radar Vivo</h1>
          <p className="text-white/35 text-sm mt-1 tracking-wide">
            América do Sul · atualizado a cada 30s
          </p>
        </div>
        <time className="text-white/25 text-xs tracking-widest tabular-nums">
          {new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
        </time>
      </div>

      {/* Contadores */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {lr ? (
          Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-24 rounded" />)
        ) : (
          <>
            <ContadorAlerta count={radar?.alertas.critico ?? 0} nivel="critico" rotulo="CRÍTICOS" />
            <ContadorAlerta count={radar?.alertas.atencao ?? 0} nivel="atencao" rotulo="ATENÇÃO" />
            <ContadorAlerta count={radar?.alertas.info    ?? 0} nivel="info"    rotulo="INFO" />
          </>
        )}
      </div>

      {/* Relatório 05h30 */}
      {radar?.relatorio_hoje && (
        <div className="border border-white/10 rounded p-6 mb-8">
          <div className="text-xs text-white/30 tracking-widest mb-3">
            RELATÓRIO 05H30 ·{' '}
            {radar.relatorio_hoje.gerado_em
              ? new Date(radar.relatorio_hoje.gerado_em).toLocaleTimeString('pt-BR', {
                  hour: '2-digit', minute: '2-digit',
                })
              : '—'}
          </div>
          <p className="text-sm text-white/75 leading-relaxed mb-5">
            {radar.relatorio_hoje.resumo_executivo}
          </p>
          {radar.relatorio_hoje.acoes_do_dia?.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs text-white/25 tracking-widest mb-2">3 AÇÕES DO DIA</div>
              {radar.relatorio_hoje.acoes_do_dia.map((acao, i) => (
                <div key={i} className="flex items-start gap-3 text-sm">
                  <span className="text-white/25 w-4 flex-shrink-0 tabular-nums">{i + 1}.</span>
                  <div>
                    <span className="text-white font-medium">{acao.titulo}</span>
                    <span className="text-white/45 ml-2 text-xs">— {acao.acao}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Filtro + lista de alertas */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div className="text-xs text-white/30 tracking-widest">ALERTAS ATIVOS</div>
          <div className="flex flex-wrap gap-1 justify-end">
            {(['todos', 'critico', 'atencao', 'info'] as NivelFiltro[]).map(n => (
              <button
                key={n}
                onClick={() => setFiltro(n)}
                className={`text-xs px-3 py-1 rounded border transition-colors ${
                  filtro === n
                    ? 'border-white/30 text-white bg-white/10'
                    : 'border-white/10 text-white/30 hover:text-white/60 hover:border-white/20'
                }`}
              >
                {n === 'todos' ? 'Todos' : n.charAt(0).toUpperCase() + n.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {la ? (
          <div className="space-y-3">
            {Array(4).fill(0).map((_, i) => <Skeleton key={i} className="h-24 rounded" />)}
          </div>
        ) : !alertas?.length ? (
          <EmptyState
            titulo={filtro === 'todos' ? 'Nenhum alerta ativo' : `Nenhum alerta de nível "${filtro}"`}
            subtitulo="O VIGÍA monitora 24h — você será notificado ao detectar algo relevante"
          />
        ) : (
          <div className="space-y-3">
            {alertas.map(a => <AlertaCard key={a.id} alerta={a} />)}
          </div>
        )}
      </div>
    </div>
  )
}
