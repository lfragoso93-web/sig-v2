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
      aria-label="Navegação principal"
    >
      {/* Primeiros 2 itens */}
      {NAV_ITEMS.slice(0, 2).map(({ to, icon: Icon, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className="flex flex-col items-center justify-center gap-0.5 flex-1 h-full text-[10px] transition-colors min-w-[44px]"
          style={({ isActive }) => ({
            color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
            fontWeight: isActive ? 600 : 400,
          })}
          aria-label={label}
        >
          <Icon size={20} aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}

      {/* Botão FAB central — Novo Lançamento
          min-width/min-height garantem área de toque ≥44px (WCAG 2.5.8) */}
      <button
        onClick={() => openTransactionModal()}
        className="flex items-center justify-center rounded-full shadow-lg transition-transform active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{
          width: 52,
          height: 52,
          minWidth: 44,
          minHeight: 44,
          background: 'var(--color-primary)',
          color: 'var(--color-text-inverse)',
          border: 'none',
          cursor: 'pointer',
          flexShrink: 0,
          // Eleva o FAB acima da linha do BottomNav para destaque visual
          marginBottom: '8px',
        }}
        aria-label="Novo Lançamento"
        title="Novo Lançamento"
      >
        <Plus size={24} aria-hidden="true" />
      </button>

      {/* Últimos 2 itens */}
      {NAV_ITEMS.slice(2).map(({ to, icon: Icon, label, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          className="flex flex-col items-center justify-center gap-0.5 flex-1 h-full text-[10px] transition-colors min-w-[44px]"
          style={({ isActive }) => ({
            color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
            fontWeight: isActive ? 600 : 400,
          })}
          aria-label={label}
        >
          <Icon size={20} aria-hidden="true" />
          <span>{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}
