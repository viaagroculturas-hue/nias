'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import clsx from 'clsx'

const LINKS = [
  { href: '/',         label: 'Radar',     short: 'Radar'    },
  { href: '/mapa',     label: 'Mapa',      short: 'Mapa'     },
  { href: '/clima',    label: 'Clima',     short: 'Clima'    },
  { href: '/mercado',  label: 'Mercado',   short: 'Merc.'    },
  { href: '/pragas',   label: 'Pragas',    short: 'Pragas'   },
  { href: '/safra',    label: 'Safra',     short: 'Safra'    },
  { href: '/demanda',  label: 'Demanda',   short: 'Dem.'     },
  { href: '/relatorio',label: 'Rel. 05h30',short: '05h30'   },
]

export default function NavBar() {
  const pathname = usePathname()

  return (
    <nav className="fixed top-0 left-0 right-0 z-40 bg-black/95 backdrop-blur border-b border-white/10 h-14 md:h-16">
      <div className="max-w-screen-2xl mx-auto px-4 md:px-6 h-full flex items-center justify-between gap-4">

        {/* Logo */}
        <Link
          href="/"
          className="text-white font-light tracking-[0.3em] text-sm flex-shrink-0"
        >
          VIGÍA
        </Link>

        {/* Links — scrollável no mobile */}
        <div className="flex items-center gap-4 md:gap-6 overflow-x-auto scrollbar-none -mr-4 pr-4">
          {LINKS.map(link => {
            const ativo = pathname === link.href
            return (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  'text-xs tracking-widest whitespace-nowrap transition-colors flex-shrink-0',
                  ativo ? 'text-white' : 'text-white/35 hover:text-white/70'
                )}
              >
                {/* Versão curta no mobile */}
                <span className="md:hidden">{link.short.toUpperCase()}</span>
                <span className="hidden md:inline">{link.label.toUpperCase()}</span>
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}
