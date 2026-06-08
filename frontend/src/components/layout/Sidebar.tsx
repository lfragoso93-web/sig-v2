import { NavLink, useParams } from 'react-router-dom'
import clsx from 'clsx'
import {
  LayoutDashboard,
  Wallet,
  TrendingUp,
  Gift,
  ArrowLeftRight,
  Settings,
  ChevronRight,
} from 'lucide-react'

// ── Logo SVG inline ─────────────────────────────────────────────────────
function SigLogo() {
  return (
    <svg
      viewBox="0 0 40 40"
      fill="none"
      aria-label="SIG v2"
      className="w-8 h-8"
    >
      {/* Fundo arredondado */}
      <rect width="40" height="40" rx="10" fill="var(--color-primary)" />
      {/* Seta de crescimento */}
      <polyline
        points="7,28 16,18 22,23 33,11"
        stroke="white"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Ponto no topo da seta */}
      <circle cx="33" cy="11" r="2.5" fill="white" />
    </svg>
  )
}

// ── Itens de navegação ─────────────────────────────────────────────────
const NAV_ITEMS = [
  { to: '',              icon: LayoutDashboard, label: 'Resumo'        },
  { to: 'rentabilidade', icon: TrendingUp,      label: 'Rentabilidade' },
  { to: 'transacoes',   icon: ArrowLeftRight,  label: 'Transações'    },
  { to: 'proventos',    icon: Gift,            label: 'Proventos'     },
]

// ── Componente ─────────────────────────────────────────────────────────────────
interface Props {
  portfolios: { id: number; name: string }[]
  selectedPortfolioId: number | null
  onSelectPortfolio: (id: number) => void
  collapsed: boolean
  onToggleCollapse: () => void
}

export default function Sidebar({
  portfolios,
  selectedPortfolioId,
  onSelectPortfolio,
  collapsed,
  onToggleCollapse,
}: Props) {
  const base = selectedPortfolioId ? `/carteira/${selectedPortfolioId}` : '#'

  return (
    <aside
      className={clsx(
        'flex flex-col h-full bg-surface border-r border-light-border dark:border-dark-border transition-all duration-200',
        collapsed ? 'w-14' : 'w-56',
      )}
    >
      {/* Logo + nome */}
      <div className="flex items-center gap-3 px-3 py-4 border-b border-light-border dark:border-dark-border">
        <SigLogo />
        {!collapsed && (
          <div className="min-w-0">
            <p className="font-bold text-sm leading-tight truncate">SIG v2</p>
            <p className="text-xs text-muted truncate">Investimentos</p>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="ml-auto text-muted hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
          aria-label={collapsed ? 'Expandir menu' : 'Recolher menu'}
        >
          <ChevronRight
            size={16}
            className={clsx('transition-transform duration-200', !collapsed && 'rotate-180')}
          />
        </button>
      </div>

      {/* Seletor de carteira */}
      {!collapsed && portfolios.length > 0 && (
        <div className="px-3 py-3 border-b border-light-border dark:border-dark-border">
          <p className="text-xs font-medium text-muted mb-1.5 uppercase tracking-wide">Carteira</p>
          <div className="flex flex-col gap-0.5">
            {portfolios.map(p => (
              <button
                key={p.id}
                onClick={() => onSelectPortfolio(p.id)}
                className={clsx(
                  'w-full text-left px-2.5 py-1.5 rounded text-sm truncate transition-colors',
                  selectedPortfolioId === p.id
                    ? 'bg-brand-primary/10 text-brand-primary font-medium'
                    : 'text-muted hover:text-gray-700 dark:hover:text-gray-300 hover:bg-surface-2'
                )}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Nav principal */}
      <nav className="flex-1 px-2 py-3 flex flex-col gap-0.5">
        {NAV_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={label}
            to={selectedPortfolioId ? `${base}/${to}` : '#'}
            end={to === ''}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-2.5 px-2.5 py-2 rounded transition-colors',
                isActive
                  ? 'bg-brand-primary/10 text-brand-primary font-medium'
                  : 'text-muted hover:text-gray-700 dark:hover:text-gray-300 hover:bg-surface-2',
                !selectedPortfolioId && 'opacity-40 pointer-events-none',
              )
            }
          >
            <Icon size={18} className="shrink-0" />
            {!collapsed && <span className="text-sm truncate">{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Rodapé - Configurações */}
      <div className="px-2 py-3 border-t border-light-border dark:border-dark-border">
        <NavLink
          to="/configuracoes"
          className={({ isActive }) =>
            clsx(
              'flex items-center gap-2.5 px-2.5 py-2 rounded transition-colors',
              isActive
                ? 'bg-brand-primary/10 text-brand-primary font-medium'
                : 'text-muted hover:text-gray-700 dark:hover:text-gray-300 hover:bg-surface-2',
            )
          }
        >
          <Settings size={18} className="shrink-0" />
          {!collapsed && <span className="text-sm">Configurações</span>}
        </NavLink>
      </div>
    </aside>
  )
}
