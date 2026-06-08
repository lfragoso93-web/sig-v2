import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  TrendingUp,
  ArrowLeftRight,
  Landmark,
  Settings,
  ChevronDown,
  Briefcase,
} from 'lucide-react'
import { usePortfolios } from '@/hooks/usePortfolios'
import { useAppStore } from '@/store/appStore'
import { useState } from 'react'

const NAV = [
  { to: '/app/dashboard',      icon: LayoutDashboard,  label: 'Resumo'       },
  { to: '/app/rentabilidade',  icon: TrendingUp,        label: 'Rentabilidade'},
  { to: '/app/transacoes',     icon: ArrowLeftRight,    label: 'Transações'   },
  { to: '/app/proventos',      icon: Landmark,          label: 'Proventos'    },
  { to: '/app/configuracoes',  icon: Settings,           label: 'Configurações'},
]

export default function Sidebar() {
  const { data: portfolios = [] } = usePortfolios()
  const { selectedPortfolioId, setSelectedPortfolio } = useAppStore()
  const [open, setOpen] = useState(false)

  const selected = portfolios.find(p => p.id === selectedPortfolioId)

  return (
    <aside
      className="flex flex-col h-full w-56 shrink-0 border-r py-5"
      style={{
        background:   'var(--color-surface)',
        borderColor:  'var(--color-divider)',
      }}
    >
      {/* Logo */}
      <div className="px-5 mb-6">
        <span className="text-base font-bold tracking-tight" style={{ color: 'var(--color-primary)' }}>
          SIG
          <span className="text-xs font-medium ml-1" style={{ color: 'var(--color-text-muted)' }}>v2</span>
        </span>
      </div>

      {/* Seletor de carteira */}
      <div className="px-3 mb-4">
        <button
          onClick={() => setOpen(o => !o)}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm border transition-colors"
          style={{
            background:  'var(--color-surface-offset)',
            borderColor: 'var(--color-border)',
            color:       'var(--color-text)',
          }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Briefcase size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
            <span className="truncate text-xs font-medium">
              {selected?.name ?? 'Selecionar carteira'}
            </span>
          </div>
          <ChevronDown size={13} className={`transition-transform ${open ? 'rotate-180' : ''}`} style={{ flexShrink: 0 }} />
        </button>

        {open && portfolios.length > 0 && (
          <div
            className="mt-1 rounded-lg border overflow-hidden"
            style={{ background: 'var(--color-surface-2)', borderColor: 'var(--color-border)', boxShadow: 'var(--shadow-md)' }}
          >
            {portfolios.map(p => (
              <button
                key={p.id}
                onClick={() => { setSelectedPortfolio(p.id); setOpen(false) }}
                className="w-full text-left px-3 py-2 text-xs transition-colors"
                style={{
                  background: selectedPortfolioId === p.id ? 'oklch(from var(--color-primary) l c h / 0.1)' : 'transparent',
                  color:      selectedPortfolioId === p.id ? 'var(--color-primary)' : 'var(--color-text)',
                  fontWeight: selectedPortfolioId === p.id ? 600 : 400,
                }}
              >
                {p.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex flex-col gap-0.5 px-3 flex-1">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'font-semibold'
                  : 'font-normal'
              }`
            }
            style={({ isActive }) => ({
              background: isActive ? 'oklch(from var(--color-primary) l c h / 0.1)' : 'transparent',
              color:      isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
            })}
          >
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
