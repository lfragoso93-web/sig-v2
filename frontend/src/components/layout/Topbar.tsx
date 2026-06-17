import { Sun, Moon, Menu, Plus } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import UserMenu from './UserMenu'
import { usePortfolios } from '@/hooks/usePortfolios'
import LogoSGI from '@/components/ui/LogoSGI'

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
      className="flex items-center justify-between gap-3 shrink-0"
      style={{
        height: '48px',
        padding: '0 16px',
        borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        background: 'var(--color-surface)',
      }}
    >
      {/* ── Esquerda ──────────────────────────────────────────── */}
      <div className="flex items-center gap-2.5 min-w-0">

        {/* Hamburger — mobile only */}
        <button
          onClick={toggleSidebar}
          className="lg:hidden flex items-center justify-center rounded-lg transition-colors"
          style={{
            color: 'var(--color-text-muted)',
            width: 32, height: 32,
            background: 'transparent',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          aria-label="Abrir menu"
        >
          <Menu size={18} />
        </button>

        {/* Logo SGI — desktop */}
        <div className="hidden lg:flex">
          <LogoSGI size={26} />
        </div>

        {/* Nome da carteira — mobile */}
        {selectedName && (
          <span
            className="lg:hidden text-xs font-semibold truncate max-w-[160px]"
            style={{ color: 'var(--color-text)' }}
          >
            {selectedName}
          </span>
        )}
      </div>

      {/* ── Direita ──────────────────────────────────────────── */}
      <div className="flex items-center gap-1.5 shrink-0">

        {/* Botão Novo Lançamento — desktop */}
        <button
          onClick={() => openTransactionModal()}
          className="hidden lg:flex items-center gap-1.5 transition-colors duration-150"
          style={{
            background:   'var(--color-primary)',
            color:        '#ffffff',
            height:       30,
            padding:      '0 12px',
            borderRadius: '8px',
            fontSize:     '0.75rem',
            fontWeight:   600,
            letterSpacing: '0.01em',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-primary-hover)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'var(--color-primary)')}
          aria-label="Novo lançamento"
        >
          <Plus size={13} strokeWidth={2.5} />
          Lançamento
        </button>

        {/* Divider visual */}
        <div
          className="hidden lg:block"
          style={{
            width: 1, height: 18,
            background: 'oklch(from var(--color-text) l c h / 0.1)',
            margin: '0 4px',
          }}
        />

        {/* Toggle tema */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="flex items-center justify-center rounded-lg transition-colors"
          style={{
            color: 'var(--color-text-muted)',
            width: 32, height: 32,
            background: 'transparent',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          aria-label="Alternar tema"
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {/* Menu do usuário */}
        <UserMenu />
      </div>
    </header>
  )
}
