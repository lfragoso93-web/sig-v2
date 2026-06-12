import { NavLink } from 'react-router-dom'
import { Sun, Moon, Plus, LogOut, User } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'
import { useAuth } from '@/contexts/AuthContext'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/carteira',               label: 'Resumo',        end: true  },
  { to: '/carteira/proventos',     label: 'Proventos',     end: false },
  { to: '/carteira/patrimonio',    label: 'Patrimônio',    end: false },
  { to: '/carteira/rentabilidade', label: 'Rentabilidade', end: false },
  { to: '/carteira/transacoes',    label: 'Transações',    end: false },
]

interface TopbarProps {
  onAddLancamento: () => void
}

export default function Topbar({ onAddLancamento }: TopbarProps) {
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()

  return (
    <header
      className="fixed top-0 inset-x-0 z-40 h-14 backdrop-blur-sm"
      style={{
        background: 'oklch(from var(--color-surface) l c h / 0.95)',
        borderBottom: '1px solid var(--color-divider)',
      }}
    >
      <div className="flex items-center h-full px-4 gap-1">

        {/* Logo */}
        <span className="mr-4 text-sm font-semibold tracking-wide shrink-0" style={{ color: 'var(--color-primary)' }}>
          SIG
          <span className="font-light" style={{ color: 'var(--color-text-faint)' }}> v2</span>
        </span>

        {/* Nav */}
        <nav className="flex items-center gap-0.5 overflow-x-auto flex-1 min-w-0 scrollbar-hide">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                clsx(
                  'shrink-0 px-3 py-1.5 rounded text-xs font-medium transition-colors duration-150',
                  isActive ? 'nav-active' : 'nav-item'
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2 ml-2 shrink-0">
          <button
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
            className="p-1.5 rounded-lg transition-colors duration-150"
            style={{ color: 'var(--color-text-muted)' }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'var(--color-surface-offset)'
              e.currentTarget.style.color = 'var(--color-text)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = ''
              e.currentTarget.style.color = 'var(--color-text-muted)'
            }}
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {user && (
            <div className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
              <User size={14} />
              <span className="hidden sm:block max-w-24 truncate">{user.name}</span>
            </div>
          )}

          <button
            onClick={logout}
            aria-label="Sair"
            className="p-1.5 rounded-lg transition-colors duration-150"
            style={{ color: 'var(--color-text-muted)' }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'oklch(from var(--color-error) l c h / 0.10)'
              e.currentTarget.style.color = 'var(--color-error)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = ''
              e.currentTarget.style.color = 'var(--color-text-muted)'
            }}
          >
            <LogOut size={16} />
          </button>

          <button
            onClick={onAddLancamento}
            className="btn btn-primary flex items-center gap-1.5 px-3 py-1.5 text-xs"
          >
            <Plus size={14} />
            Novo Lançamento
          </button>
        </div>
      </div>
    </header>
  )
}
