'use client'

import { useEffect, useRef, useState } from 'react'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Etapa {
  etapa: number
  nome: string
  status: 'pendente' | 'rodando' | 'concluido' | 'erro'
  pct_concluido: number
  registros_processados: number
  registros_total: number
}

interface SeedData {
  iniciado: boolean
  pct_total: number
  concluido: boolean
  etapas: Etapa[]
  com_erro?: number
  etapas_previstas?: { etapa: number; nome: string; duracao_estimada_min: number }[]
}

// Todas as 10 etapas para mostrar desde o início
const ETAPAS_PREVISTAS = [
  { etapa: 1,  nome: 'Municípios América do Sul',        duracao: 5 },
  { etapa: 2,  nome: '85 culturas e calendários',        duracao: 2 },
  { etapa: 3,  nome: 'Histórico de produção IBGE',       duracao: 20 },
  { etapa: 4,  nome: 'Histórico de preços CEPEA',        duracao: 10 },
  { etapa: 5,  nome: 'Dados climáticos INMET',           duracao: 15 },
  { etapa: 6,  nome: 'ENSO + NOAA',                      duracao: 3 },
  { etapa: 7,  nome: 'Fatores de demanda',               duracao: 2 },
  { etapa: 8,  nome: 'Viveiros RENASEM',                 duracao: 5 },
  { etapa: 9,  nome: 'Processamento satelital GEE',      duracao: 120 },
  { etapa: 10, nome: 'Geração de alertas iniciais',      duracao: 3 },
]

function IconeEtapa({ status }: { status: string }) {
  if (status === 'concluido') return <span className="text-green-400 w-4">✓</span>
  if (status === 'rodando')   return <span className="text-white w-4 animate-pulse">●</span>
  if (status === 'erro')      return <span className="text-red-400 w-4">✗</span>
  return                             <span className="text-white/20 w-4">○</span>
}

function TempoEstimado({ minutos }: { minutos: number }) {
  if (minutos >= 60) return <span>{Math.round(minutos / 60)}h</span>
  return <span>{minutos}min</span>
}

interface Props {
  onConcluido: () => void
}

export default function SeedProgress({ onConcluido }: Props) {
  const [data, setData] = useState<SeedData | null>(null)
  const [erro, setErro] = useState<string | null>(null)
  const [tempoInicio] = useState(Date.now())
  const [tempoDecorrido, setTempoDecorrido] = useState(0)
  const esRef = useRef<EventSource | null>(null)

  // Cronômetro
  useEffect(() => {
    const t = setInterval(() => setTempoDecorrido(Math.floor((Date.now() - tempoInicio) / 1000)), 1000)
    return () => clearInterval(t)
  }, [tempoInicio])

  // SSE para progresso em tempo real
  useEffect(() => {
    const conectar = () => {
      const es = new EventSource(`${API}/api/seed/stream`)
      esRef.current = es

      es.onmessage = (e) => {
        try {
          const parsed: SeedData & { encerrar?: boolean; erro?: string } = JSON.parse(e.data)

          if (parsed.erro) {
            setErro(parsed.erro)
            return
          }

          setData(parsed)
          setErro(null)

          if (parsed.encerrar || parsed.concluido) {
            es.close()
            // Pequeno delay para o usuário ver 100%
            setTimeout(onConcluido, 1500)
          }
        } catch {
          // ignore parse errors
        }
      }

      es.onerror = () => {
        es.close()
        // Reconectar após 3s se ainda não concluído
        if (!data?.concluido) {
          setTimeout(conectar, 3000)
        }
      }
    }

    conectar()
    return () => esRef.current?.close()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const formatarTempo = (s: number) => {
    const m = Math.floor(s / 60)
    const ss = s % 60
    return m > 0 ? `${m}m ${ss}s` : `${ss}s`
  }

  const etapasVisiveis = ETAPAS_PREVISTAS.map(ep => {
    const real = data?.etapas?.find(e => e.etapa === ep.etapa)
    return {
      ...ep,
      status: real?.status || 'pendente',
      pct_concluido: real?.pct_concluido || 0,
      registros_processados: real?.registros_processados || 0,
      registros_total: real?.registros_total || 0,
    }
  })

  const pctTotal = data?.pct_total || 0
  const etapaAtual = etapasVisiveis.find(e => e.status === 'rodando')

  return (
    <div className="fixed inset-0 bg-black z-50 flex flex-col items-center justify-center px-4 md:px-6 py-8 md:py-12 overflow-y-auto">
      {/* Logo */}
      <div className="text-white font-light tracking-[0.5em] text-2xl mb-2">
        VIGÍA
      </div>
      <div className="text-white/30 text-xs tracking-[0.3em] mb-8 md:mb-12">
        INTELIGÊNCIA AGROESTRATÉGICA
      </div>

      {/* Barra de progresso principal */}
      <div className="w-full max-w-sm mb-8">
        <div className="flex justify-between text-xs text-white/30 mb-2 tracking-wide">
          <span>INICIALIZANDO</span>
          <span>{pctTotal.toFixed(0)}%</span>
        </div>
        <div className="bg-white/10 h-px w-full">
          <div
            className="bg-white h-px transition-all duration-700 ease-out"
            style={{ width: `${pctTotal}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-white/20 mt-2">
          <span>{etapaAtual ? etapaAtual.nome : data?.concluido ? 'Concluído' : 'Aguardando...'}</span>
          <span>{formatarTempo(tempoDecorrido)}</span>
        </div>
      </div>

      {/* Lista de etapas */}
      <div className="w-full max-w-sm space-y-1.5">
        {etapasVisiveis.map(ep => (
          <div key={ep.etapa} className="flex items-center gap-3">
            <IconeEtapa status={ep.status} />
            <div className="flex-1 min-w-0">
              <div className={`text-xs truncate ${
                ep.status === 'concluido' ? 'text-white/50' :
                ep.status === 'rodando'   ? 'text-white' :
                ep.status === 'erro'      ? 'text-red-400' :
                'text-white/20'
              }`}>
                {ep.nome}
              </div>
              {/* Barra secundária para etapa em andamento */}
              {ep.status === 'rodando' && ep.registros_total > 0 && (
                <div className="mt-0.5 bg-white/10 h-px w-full">
                  <div
                    className="bg-white/50 h-px transition-all duration-300"
                    style={{ width: `${ep.pct_concluido}%` }}
                  />
                </div>
              )}
              {ep.status === 'rodando' && ep.registros_total > 0 && (
                <div className="text-xs text-white/30 mt-0.5">
                  {ep.registros_processados.toLocaleString()} / {ep.registros_total.toLocaleString()}
                </div>
              )}
            </div>
            <div className="text-xs text-white/20 flex-shrink-0">
              {ep.status === 'pendente' && <TempoEstimado minutos={ep.duracao} />}
              {ep.status === 'rodando' && (
                <span className="text-white/40">{ep.pct_concluido.toFixed(0)}%</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Erro */}
      {erro && (
        <div className="mt-8 text-red-400 text-xs text-center max-w-sm">
          Erro: {erro}
        </div>
      )}

      {/* Nota de rodapé */}
      <div className="mt-12 text-white/15 text-xs text-center max-w-xs leading-relaxed">
        Primeiro boot — coletando dados de 4.500+ municípios,
        85 culturas e fontes climáticas da América do Sul.
      </div>
    </div>
  )
}
