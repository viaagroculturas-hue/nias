import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'VIGÍA — Inteligência Agroestratégica',
  description: 'Monitoramento agroestratégico da América do Sul',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="bg-black text-white antialiased">
        {children}
      </body>
    </html>
  )
}
