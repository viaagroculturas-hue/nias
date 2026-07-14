'use client'

import { useEffect, useState } from 'react'

interface TerraProps {
  terra: {
    id: string
    cultura: string
    situacao: string
    risco: string
    janela_horas: number
    acao_exata: string
    patrimonio_em_risco: number
    confianca_pct: number
    fontes?: string[]
    disparado_em?: string
  }
  onReconhecer: () => void
}

function useCountdown(horas: number, disparado_em?: string): string {
  const [restante, setRestante] = useState('')

  useEffect(() => {
    const calcular = () => {
      const base = disparado_em ? new Date(disparado_em) : new Date()
      const fim = new Date(base.getTime() + horas * 3_600_000)
      const diff = fim.getTime() - Date.now()
      if (diff <= 0) return setRestante('EXPIRADO')
      const h = Math.floor(diff / 3_600_000)
      const m = Math.floor((diff % 3_600_000) / 60_000)
      const s = Math.floor((diff % 60_000) / 1_000)
      setRestante(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`)
    }
    calcular()
    const t = setInterval(calcular, 1000)
    return () => clearInterval(t)
  }, [horas, disparado_em])

  return restante
}

export default function TerraOverlay({ terra, onReconhecer }: TerraProps) {
  const [confirmando, setConfirmando] = useState(false)
  const countdown = useCountdown(terra.janela_horas, terra.disparado_em)

  const patStr = terra.patrimonio_em_risco?.toLocaleString('pt-BR', {
    style: 'currency', currency: 'BRL', maximumFractionDigits: 0,
  }) ?? '—'

  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: '#000' }}>
      {/* Barra de urgência no topo */}
      <div className="h-1 bg-white/20" style={{ animation: 'pulse 1.5s ease-in-out infinite' }} />

      <div className="flex-1 flex flex-col items-center justify-center px-4 md:px-6 py-12">

        {/* TERRA */}
        <div
          className="font-light tracking-[0.5em] text-white mb-4 select-none"
          style={{
            fontSize: 'clamp(3.5rem, 14vw, 9rem)',
            animation: 'pulse 2s ease-in-out infinite',
          }}
        >
          TERRA
        </div>

        {/* Countdown */}
        <div className="mb-8 text-center">
          <div className="text-white/25 text-xs tracking-widest mb-1">JANELA DE AÇÃO</div>
          <div className={`text-3xl font-mono font-light tabular-nums ${
            countdown === 'EXPIRADO' ? 'text-red-500' : 'text-white'
          }`}>
            {countdown || `${terra.janela_horas}h`}
          </div>
        </div>

        {/* Cultura + situação */}
        <div className="max-w-xl text-center mb-8">
          <div className="text-red-400 text-xl mb-3 font-light tracking-wide">
            {terra.cultura.replace('_', ' ')}
          </div>
          <p className="text-white/75 text-base leading-relaxed">
            {terra.situacao}
          </p>
        </div>

        {/* Métricas */}
        <div className="flex gap-8 text-white/40 text-sm mb-10 flex-wrap justify-center">
          <div className="text-center">
            <div className="text-white/20 text-xs tracking-widest mb-1">PATRIMÔNIO EM RISCO</div>
            <div className="text-red-400 font-light">{patStr}</div>
          </div>
          <div className="text-center">
            <div className="text-white/20 text-xs tracking-widest mb-1">CONFIANÇA</div>
            <div className="text-white font-light">{terra.confianca_pct}%</div>
          </div>
          {terra.fontes?.length ? (
            <div className="text-center">
              <div className="text-white/20 text-xs tracking-widest mb-1">FONTES</div>
              <div className="text-white/50 font-light text-xs">{terra.fontes.join(' · ')}</div>
            </div>
          ) : null}
        </div>

        {/* Ação */}
        <div className="w-full max-w-md mb-6">
          <div className="text-white/20 text-xs tracking-widest mb-2 text-center">AÇÃO IMEDIATA</div>
          <div className="border border-white/20 rounded p-4 text-center text-white/80 text-sm leading-relaxed">
            {terra.acao_exata}
          </div>
        </div>

        {/* Botões */}
        <button
          className="bg-white text-black w-full max-w-xs py-4 text-sm font-medium tracking-widest hover:bg-gray-100 transition-colors mb-4"
          onClick={() => {
            navigator.clipboard?.writeText(terra.acao_exata).catch(() => {})
          }}
        >
          COPIAR AÇÃO
        </button>

        {!confirmando ? (
          <button
            onClick={() => setConfirmando(true)}
            className="text-white/25 text-sm underline hover:text-white/50 transition-colors"
          >
            Reconhecer alerta
          </button>
        ) : (
          <div className="text-center">
            <p className="text-white/50 text-sm mb-3">
              Confirma que leu o alerta e tomará providências?
            </p>
            <div className="flex gap-4 justify-center">
              <button
                onClick={onReconhecer}
                className="border border-white/20 text-white text-sm px-6 py-2 hover:bg-white/10 transition-colors"
              >
                Sim, reconheço
              </button>
              <button
                onClick={() => setConfirmando(false)}
                className="text-white/30 text-sm px-6 py-2"
              >
                Cancelar
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
