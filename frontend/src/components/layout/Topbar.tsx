import { NavLink } from 'react-router-dom'
import { Sun, Moon, Plus, LogOut, User } from 'lucide-react'
import { useTheme } from '@/contexts/ThemeContext'
import { useAuth } from '@/contexts/AuthContext'
import clsx from 'clsx'

const NAV_ITEMS = [
  { to: '/resumo',        label: 'Resumo' },
  { to: '/proventos',     label: 'Proventos' },
  { to: '/patrimonio',    label: 'Patrimônio' },
  { to: '/rentabilidade', label: 'Rentabilidade' },
  { to: '/metas',         label: 'Metas' },
  { to: '/analise',       label: 'Análise' },
  { to: '/lancamentos',   label: 'Lançamentos' },
  { to: '/irpf',          label: 'IRPF' },
]

interface TopbarProps {
  onAddLancamento: () => void
}

export default function Topbar({ onAddLancamento }: TopbarProps) {
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()

  return (
    <header className="fixed top-0 inset-x-0 z-40 h-14
      bg-surface-900/95 border-b border-surface-700
      backdrop-blur-sm">
      <div className="flex items-center h-full px-4 gap-1">

        {/* Logo */}
        <span className="mr-4 text-sm font-semibold text-brand-400 tracking-wide shrink-0">
          SIG
          <span className="text-slate-500 font-light"> v2</span>
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
                    ? 'text-brand-400 bg-brand-600/15'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-surface-700'
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
            className="p-1.5 rounded-lg text-slate-400
              hover:bg-surface-700 hover:text-slate-200
              transition-colors duration-150"
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* User */}
          {user && (
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <User size={14} />
              <span className="hidden sm:block max-w-24 truncate">{user.name}</span>
            </div>
          )}

          {/* Logout */}
          <button
            onClick={logout}
            aria-label="Sair"
            className="p-1.5 rounded-lg text-slate-400
              hover:bg-red-500/10 hover:text-red-400
              transition-colors duration-150"
          >
            <LogOut size={16} />
          </button>

          {/* Add Lancamento */}
          <button
            onClick={onAddLancamento}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md
              text-xs font-medium bg-brand-600 hover:bg-brand-500
              text-white transition-colors duration-150"
          >
            <Plus size={14} />
            Adicionar Lançamento
          </button>
        </div>
      </div>
    </header>
  )
}
