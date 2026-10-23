import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Wallet,
  TrendingUp,
  ArrowLeftRight,
  Landmark,
  Plus,
} from 'lucide-react'
import { useAppStore } from '@/store/appStore'

const LEFT_NAV_ITEMS = [
  { to: '/carteira',               icon: LayoutDashboard, label: 'Resumo',        end: true  },
  { to: '/carteira/patrimonio',    icon: Wallet,          label: 'Patrimônio',    end: false },
  { to: '/carteira/rentabilidade', icon: TrendingUp,      label: 'Rentabilidade', end: false },
]

const RIGHT_NAV_ITEMS = [
  { to: '/carteira/transacoes',    icon: ArrowLeftRight,  label: 'Transações',    end: false },
  { to: '/carteira/proventos',     icon: Landmark,        label: 'Proventos',     end: false },
]

export const BOTTOM_NAV_ITEMS = [...LEFT_NAV_ITEMS, ...RIGHT_NAV_ITEMS]

export default function BottomNav() {
  const { openTransactionModal } = useAppStore()

  return (
    <nav
      className="lg:hidden fixed bottom-0 inset-x-0 z-30 flex items-center justify-around px-1"
      style={{
        height: '62px',
        background: 'var(--color-surface)',
        borderTop: '1px solid var(--color-divider)',
        boxShadow: '0 -2px 12px oklch(0 0 0 / 0.06)',
        paddingBottom: 'env(safe-area-inset-bottom)',
      }}
      aria-label="Navegação principal"
    >
      {/* Itens à esquerda do FAB */}
      {LEFT_NAV_ITEMS.map(({ to, icon: Icon, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className="flex flex-col items-center justify-center gap-0.5 flex-1 h-full text-[10px] transition-colors min-w-[44px] px-0.5"
          style={({ isActive }) => ({
            color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
            fontWeight: isActive ? 600 : 450,
          })}
          aria-label={label}
        >
          <Icon size={19} strokeWidth={1.9} aria-hidden="true" />
          <span className="truncate max-w-full leading-tight">{label}</span>
        </NavLink>
      ))}

      {/* Botão FAB central — Novo Lançamento
          min-width/min-height garantem área de toque ≥44px (WCAG 2.5.8) */}
      <button
        type="button"
        onClick={() => openTransactionModal()}
        className="flex items-center justify-center rounded-full shadow-lg transition-transform active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 mx-1"
        style={{
          width: 48,
          height: 48,
          minWidth: 44,
          minHeight: 44,
          background: 'var(--color-primary)',
          color: 'var(--color-text-inverse)',
          border: '2px solid var(--color-surface)',
          cursor: 'pointer',
          flexShrink: 0,
          marginBottom: '10px',
        }}
        aria-label="Novo Lançamento"
        title="Novo Lançamento"
      >
        <Plus size={22} strokeWidth={2.25} aria-hidden="true" />
      </button>

      {/* Itens à direita do FAB */}
      {RIGHT_NAV_ITEMS.map(({ to, icon: Icon, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className="flex flex-col items-center justify-center gap-0.5 flex-1 h-full text-[10px] transition-colors min-w-[44px] px-0.5"
          style={({ isActive }) => ({
            color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
            fontWeight: isActive ? 600 : 450,
          })}
          aria-label={label}
        >
          <Icon size={19} strokeWidth={1.9} aria-hidden="true" />
          <span className="truncate max-w-full leading-tight">{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
