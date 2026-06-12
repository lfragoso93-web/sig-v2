import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Wallet,
  ArrowLeftRight,
  Landmark,
  Plus,
} from 'lucide-react'
import { useAppStore } from '@/store/appStore'

const NAV_ITEMS = [
  { to: '/carteira',              icon: LayoutDashboard, label: 'Resumo',     end: true  },
  { to: '/carteira/patrimonio',   icon: Wallet,          label: 'Patrimônio', end: false },
  { to: '/carteira/transacoes',   icon: ArrowLeftRight,  label: 'Transações', end: false },
  { to: '/carteira/proventos',    icon: Landmark,        label: 'Proventos',  end: false },
]

export default function BottomNav() {
  const { openTransactionModal } = useAppStore()

  return (
    <nav
      className="lg:hidden fixed bottom-0 inset-x-0 z-30 flex items-center justify-around"
      style={{
        height: '60px',
        background: 'var(--color-surface)',
        borderTop: '1px solid var(--color-divider)',
        paddingBottom: 'env(safe-area-inset-bottom)', // suporte a notch iOS
      }}
    >
      {/* Primeiros 2 itens */}
      {NAV_ITEMS.slice(0, 2).map(({ to, icon: Icon, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className="flex flex-col items-center justify-center gap-0.5 flex-1 h-full text-[10px] transition-colors"
          style={({ isActive }) => ({
            color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
            fontWeight: isActive ? 600 : 400,
          })}
        >
          <Icon size={20} />
          {label}
        </NavLink>
      ))}

      {/* Botão FAB central — Novo Lançamento */}
      <button
        onClick={() => openTransactionModal()}
        className="flex items-center justify-center rounded-full shadow-lg transition-transform active:scale-95"
        style={{
          width: 48,
          height: 48,
          background: 'var(--color-primary)',
          color: 'var(--color-text-inverse)',
          border: 'none',
          cursor: 'pointer',
          flexShrink: 0,
        }}
        aria-label="Novo Lançamento"
      >
        <Plus size={22} />
      </button>

      {/* Últimos 2 itens */}
      {NAV_ITEMS.slice(2).map(({ to, icon: Icon, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className="flex flex-col items-center justify-center gap-0.5 flex-1 h-full text-[10px] transition-colors"
          style={({ isActive }) => ({
            color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
            fontWeight: isActive ? 600 : 400,
          })}
        >
          <Icon size={20} />
          {label}
        </NavLink>
      ))}
    </nav>
  )
}
