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
        height:       'var(--topbar-height, 56px)',
        padding:      '0 clamp(1rem, 2vw, 1.5rem)',
        gap:          '12px',
        background:   'var(--color-surface)',
        borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        /* Sombra sutil para separar o header do conteúdo */
        boxShadow:    '0 1px 4px oklch(0.18 0.01 80 / 0.05)',
      }}
    >
      {/* ── Esquerda ───────────────────────────────────────────── */}
      <div className="flex items-center min-w-0" style={{ gap: 10 }}>

        {/* Hamburger — mobile only */}
        <button
          onClick={toggleSidebar}
          className="lg:hidden btn-icon"
          aria-label="Abrir menu"
        >
          <Menu size={18} />
        </button>

        {/* Logo — desktop */}
        <div className="hidden lg:flex">
          <LogoSGI size={28} />
        </div>

        {/* Nome da carteira — mobile */}
        {selectedName && (
          <span
            className="lg:hidden truncate"
            style={{
              fontSize:   'var(--text-sm)',
              fontWeight: 550,
              maxWidth:   160,
              color:      'var(--color-text)',
              letterSpacing: '-0.005em',
            }}
          >
            {selectedName}
          </span>
        )}
      </div>

      {/* ── Direita ───────────────────────────────────────────── */}
      <div className="flex items-center shrink-0" style={{ gap: 6 }}>

        {/* Botão Novo Lançamento — desktop */}
        <button
          onClick={() => openTransactionModal()}
          className="hidden lg:inline-flex items-center btn btn-primary"
          style={{
            height:     34,
            padding:    '0 14px',
            fontSize:   'var(--text-xs)',
            fontWeight: 600,
            gap:        6,
            /* Sombra colorida para dar presença ao CTA */
            boxShadow:  '0 1px 4px oklch(from var(--color-primary) 0.3 c h / 0.45)',
          }}
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
            height:     20,
            background: 'oklch(from var(--color-text) l c h / 0.08)',
            margin:     '0 4px',
            flexShrink: 0,
          }}
        />

        {/* Toggle tema */}
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="btn-icon"
          aria-label="Alternar tema"
        >
          {theme === 'dark'
            ? <Sun  size={16} strokeWidth={1.75} />
            : <Moon size={16} strokeWidth={1.75} />}
        </button>

        {/* Menu do usuário */}
        <UserMenu />
      </div>
    </header>
  )
}
