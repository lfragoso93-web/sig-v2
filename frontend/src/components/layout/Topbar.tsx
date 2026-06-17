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
      className="flex items-center justify-between shrink-0"
      style={{
        height:       '52px',
        padding:      '0 20px',
        gap:          '12px',
        borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        background:   'var(--color-surface)',
      }}
    >
      {/* ── Esquerda ───────────────────────────────────────── */}
      <div className="flex items-center min-w-0" style={{ gap: 10 }}>

        {/* Hamburger — mobile only */}
        <button
          onClick={toggleSidebar}
          className="lg:hidden flex items-center justify-center rounded-lg transition-colors"
          style={{
            color:      'var(--color-text-muted)',
            width:      34,
            height:     34,
            background: 'transparent',
            flexShrink: 0,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          aria-label="Abrir menu"
        >
          <Menu size={18} />
        </button>

        {/* Logo — desktop */}
        <div className="hidden lg:flex">
          <LogoSGI size={26} />
        </div>

        {/* Nome da carteira — mobile */}
        {selectedName && (
          <span
            className="lg:hidden truncate"
            style={{
              fontSize:   'var(--text-xs)',
              fontWeight: 600,
              maxWidth:   160,
              color:      'var(--color-text)',
            }}
          >
            {selectedName}
          </span>
        )}
      </div>

      {/* ── Direita ───────────────────────────────────────── */}
      <div className="flex items-center shrink-0" style={{ gap: 6 }}>

        {/* Botão Novo Lançamento — desktop */}
        <button
          onClick={() => openTransactionModal()}
          className="hidden lg:inline-flex items-center transition-colors duration-150"
          style={{
            background:    'var(--color-primary)',
            color:         '#ffffff',
            height:        32,
            padding:       '0 14px',
            borderRadius:  'var(--radius-lg)',
            fontSize:      'var(--text-xs)',
            fontWeight:    600,
            letterSpacing: '0.01em',
            gap:           6,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-primary-hover)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'var(--color-primary)')}
          aria-label="Novo lançamento"
        >
          <Plus size={13} strokeWidth={2.5} />
          Lançamento
        </button>

        {/* Divisor visual */}
        <div
          className="hidden lg:block"
          style={{
            width:      1,
            height:     18,
            background: 'oklch(from var(--color-text) l c h / 0.09)',
            margin:     '0 2px',
            flexShrink: 0,
          }}
        />

        {/* Toggle tema */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="flex items-center justify-center rounded-lg transition-colors"
          style={{
            color:      'var(--color-text-muted)',
            width:      34,
            height:     34,
            background: 'transparent',
            flexShrink: 0,
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
