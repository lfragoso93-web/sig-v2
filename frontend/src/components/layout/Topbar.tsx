import { Sun, Moon, Menu } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import UserMenu from './UserMenu'
import { usePortfolios } from '@/hooks/usePortfolios'

export default function Topbar() {
  const {
    theme, setTheme,
    toggleSidebar,
    selectedPortfolioId,
    openTransactionModal,
  } = useAppStore()

  const { data: portfolios = [] } = usePortfolios()
  const selectedName = portfolios.find(p => p.id === selectedPortfolioId)?.name

  return (
    <header
      className="flex items-center justify-between gap-2 px-3 lg:px-5 shrink-0"
      style={{
        height: '52px',
        borderBottom: '1px solid var(--color-divider)',
        background: 'var(--color-surface)',
      }}
    >
      {/* Esquerda: hamburger (mobile) + logo/carteira */}
      <div className="flex items-center gap-2 min-w-0">
        {/* Hamburger — só aparece em <lg */}
        <button
          onClick={toggleSidebar}
          className="lg:hidden flex items-center justify-center p-1.5 rounded-md transition-colors"
          style={{ color: 'var(--color-text-muted)', minWidth: 36, minHeight: 36 }}
          aria-label="Abrir menu"
        >
          <Menu size={20} />
        </button>

        {/* Nome da carteira selecionada — só mobile */}
        {selectedName && (
          <span
            className="lg:hidden text-xs font-medium truncate max-w-[140px]"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {selectedName}
          </span>
        )}
      </div>

      {/* Direita: tema + user menu + botão novo lançamento (desktop) */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Botão Novo Lançamento — só desktop (mobile usa FAB) */}
        <button
          onClick={() => openTransactionModal()}
          className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors duration-150"
          style={{
            background: 'var(--color-primary)',
            color: 'var(--color-text-inverse)',
          }}
        >
          + Novo Lançamento
        </button>

        {/* Toggle tema */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="flex items-center justify-center p-1.5 rounded-md transition-colors"
          style={{ color: 'var(--color-text-muted)', minWidth: 36, minHeight: 36 }}
          aria-label="Alternar tema"
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>

        {/* Menu do usuário */}
        <UserMenu />
      </div>
    </header>
  )
}
