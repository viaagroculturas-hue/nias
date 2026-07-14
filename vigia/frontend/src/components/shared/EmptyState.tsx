interface EmptyStateProps {
  titulo: string
  subtitulo?: string
  icone?: string
}

export default function EmptyState({ titulo, subtitulo, icone = '—' }: EmptyStateProps) {
  return (
    <div className="border border-white/8 rounded p-8 md:p-12 text-center">
      <div className="text-white/15 text-3xl mb-3 font-light">{icone}</div>
      <div className="text-white/30 text-sm mb-1">{titulo}</div>
      {subtitulo && (
        <div className="text-white/15 text-xs leading-relaxed max-w-xs mx-auto">
          {subtitulo}
        </div>
      )}
    </div>
  )
}
