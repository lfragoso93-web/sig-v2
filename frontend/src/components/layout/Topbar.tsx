import { NavLink } from 'react-router-dom'
import { Sun, Moon, Plus, LogOut, User } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'
import { useAuth } from '@/contexts/AuthContext'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/resumo',       label: 'Resumo' },
  { to: '/proventos',    label: 'Proventos' },
  { to: '/patrimonio',   label: 'Patrimônio' },
  { to: '/rentabilidade',label: 'Rentabilidade' },
  { to: '/metas',        label: 'Metas' },
  { to: '/analise',      label: 'Análise' },
  { to: '/lancamentos',  label: 'Lançamentos' },
  { to: '/irpf',         label: 'IRPF' },
]

interface TopbarProps {
  onAddLancamento: () => void
}

export default function Topbar({ onAddLancamento }: TopbarProps) {
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()

  return (
    <header className="fixed top-0 inset-x-0 z-40 h-14
      bg-white/90 dark:bg-dark-700/90
      border-b border-light-border dark:border-dark-border
      backdrop-blur-sm">
      <div className="flex items-center h-full px-4 gap-1">

        {/* Logo */}
        <span className="mr-4 text-sm font-semibold text-brand-primary tracking-wide shrink-0">
          SIG
          <span className="text-gray-400 dark:text-gray-500 font-light"> v2</span>
        </span>

        {/* Nav */}
        <nav className="flex items-center gap-0.5 overflow-x-auto flex-1 min-w-0 scrollbar-hide">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                clsx(
                  'shrink-0 px-3 py-1.5 rounded text-xs font-medium transition-colors duration-150',
                  isActive
                    ? 'text-brand-primary bg-brand-primary/10'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-light-100 dark:hover:bg-dark-600'
                )
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-2 ml-2 shrink-0">
          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro'}
            className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400
              hover:bg-light-100 dark:hover:bg-dark-600
              hover:text-gray-800 dark:hover:text-gray-200
              transition-colors duration-150"
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* User */}
          {user && (
            <div className="flex items-center gap-1 text-xs text-muted">
              <User size={14} />
              <span className="hidden sm:block max-w-24 truncate">{user.name}</span>
            </div>
          )}

          {/* Logout */}
          <button
            onClick={logout}
            aria-label="Sair"
            className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400
              hover:bg-rose-500/10 hover:text-rose-500
              transition-colors duration-150"
          >
            <LogOut size={16} />
          </button>

          {/* Add Lancamento */}
          <button
            onClick={onAddLancamento}
            className="btn-primary text-xs px-3 py-1.5"
          >
            <Plus size={14} />
            Adicionar Lançamento
          </button>
        </div>
      </div>
    </header>
  )
}
