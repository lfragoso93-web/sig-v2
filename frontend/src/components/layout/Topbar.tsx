import { Sun, Moon, Menu, Plus, Briefcase, ChevronDown, CheckCircle2 } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '@/store/appStore'
import UserMenu from './UserMenu'
import { usePortfolios } from '@/hooks/usePortfolios'
import LogoSGI from '@/components/ui/LogoSGI'
import CreatePortfolioModal from '@/components/modals/CreatePortfolioModal'

function PortfolioSelector() {
  const { data: portfolios = [] } = usePortfolios()
  const { selectedPortfolioId, setSelectedPortfolio } = useAppStore()
  const [open, setOpen] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selected = portfolios.find(p => p.id === selectedPortfolioId)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Sem carteiras: mostra botão para criar
  if (!portfolios.length) {
    return (
      <>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '5px 10px', height: 32,
            borderRadius: 'var(--radius-lg)',
            border: '1px dashed oklch(from var(--color-primary) l c h / 0.4)',
            background: 'oklch(from var(--color-primary) l c h / 0.06)',
            color: 'var(--color-primary)',
            fontSize: 'var(--text-xs)', fontWeight: 550,
            cursor: 'pointer',
          }}
          aria-label="Criar carteira"
        >
          <Briefcase size={12} />
          <span>Criar carteira</span>
        </button>
        {showCreate && <CreatePortfolioModal onClose={() => setShowCreate(false)} />}
      </>
    )
  }

  return (
    <>
      <div ref={ref} className="relative">
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 rounded-lg transition-all"
          style={{
            padding: '5px 10px', height: 32,
            background: open
              ? 'oklch(from var(--color-primary) l c h / 0.1)'
              : 'oklch(from var(--color-text) l c h / 0.05)',
            border: open
              ? '1px solid oklch(from var(--color-primary) l c h / 0.3)'
              : '1px solid oklch(from var(--color-text) l c h / 0.09)',
            color: 'var(--color-text)',
            transition: 'all 150ms cubic-bezier(0.16,1,0.3,1)',
            maxWidth: 220,
          }}
          onMouseEnter={e => {
            if (!open) {
              e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.08)'
              e.currentTarget.style.borderColor = 'oklch(from var(--color-text) l c h / 0.13)'
            }
          }}
          onMouseLeave={e => {
            if (!open) {
              e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.05)'
              e.currentTarget.style.borderColor = 'oklch(from var(--color-text) l c h / 0.09)'
            }
          }}
          aria-label="Selecionar carteira"
        >
          <Briefcase size={12} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
          <span className="truncate" style={{ fontSize: 'var(--text-xs)', fontWeight: 550, maxWidth: 140 }}>
            {selected?.name ?? 'Carteira'}
          </span>
          <ChevronDown
            size={11}
            style={{
              color: 'var(--color-text-muted)', flexShrink: 0,
              transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 180ms cubic-bezier(0.16,1,0.3,1)',
            }}
          />
        </button>

        {open && (
          <div
            className="absolute left-0 z-50"
            style={{
              top: 'calc(100% + 6px)', minWidth: 180,
              background: 'var(--color-surface-2)',
              border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-lg)',
              overflow: 'hidden', padding: 6,
            }}
          >
            {portfolios.map(p => (
              <button
                key={p.id}
                onClick={() => { setSelectedPortfolio(p.id); setOpen(false) }}
                className="w-full flex items-center justify-between rounded-lg transition-all"
                style={{
                  padding: '7px 11px',
                  fontSize: 'var(--text-xs)',
                  fontWeight: p.id === selectedPortfolioId ? 550 : 400,
                  color: p.id === selectedPortfolioId ? 'var(--color-primary)' : 'var(--color-text)',
                  background: p.id === selectedPortfolioId
                    ? 'oklch(from var(--color-primary) l c h / 0.08)'
                    : 'transparent',
                }}
                onMouseEnter={e => {
                  if (p.id !== selectedPortfolioId)
                    e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.05)'
                }}
                onMouseLeave={e => {
                  if (p.id !== selectedPortfolioId)
                    e.currentTarget.style.background = 'transparent'
                }}
              >
                <span className="truncate">{p.name}</span>
                {p.id === selectedPortfolioId && (
                  <CheckCircle2 size={12} style={{ color: 'var(--color-primary)', flexShrink: 0, marginLeft: 6 }} />
                )}
              </button>
            ))}

            {/* Divisór + criar nova */}
            <div style={{ height: 1, background: 'oklch(from var(--color-text) l c h / 0.07)', margin: '4px 0' }} />
            <button
              onClick={() => { setOpen(false); setShowCreate(true) }}
              className="w-full flex items-center gap-2 rounded-lg"
              style={{
                padding: '7px 11px',
                fontSize: 'var(--text-xs)', fontWeight: 500,
                color: 'var(--color-primary)', background: 'transparent',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.06)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <Plus size={11} />
              Nova carteira
            </button>
          </div>
        )}
      </div>

      {showCreate && <CreatePortfolioModal onClose={() => setShowCreate(false)} />}
    </>
  )
}

export default function Topbar() {
  const { theme, setTheme, toggleSidebar, openTransactionModal } = useAppStore()

  return (
    <header
      className="flex items-center justify-between shrink-0"
      style={{
        height: 'var(--topbar-height, 56px)',
        padding: '0 clamp(1rem, 2vw, 1.5rem)',
        gap: 12,
        background: 'var(--color-surface)',
        borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        boxShadow: '0 1px 4px oklch(0.18 0.01 80 / 0.05)',
        position: 'relative', zIndex: 30,
      }}
    >
      {/* Esquerda */}
      <div className="flex items-center min-w-0" style={{ gap: 10 }}>
        <button onClick={toggleSidebar} className="lg:hidden btn-icon" aria-label="Abrir menu">
          <Menu size={18} />
        </button>
        <LogoSGI size={28} />
        <div
          className="hidden sm:block"
          style={{ width: 1, height: 18, background: 'oklch(from var(--color-text) l c h / 0.1)', flexShrink: 0 }}
        />
        <div className="hidden sm:block">
          <PortfolioSelector />
        </div>
      </div>

      {/* Direita */}
      <div className="flex items-center shrink-0" style={{ gap: 6 }}>
        <button
          onClick={() => openTransactionModal()}
          className="hidden sm:inline-flex items-center btn btn-primary"
          style={{ height: 34, padding: '0 14px', fontSize: 'var(--text-xs)', fontWeight: 600, gap: 6,
            boxShadow: '0 1px 4px oklch(from var(--color-primary) 0.3 c h / 0.45)' }}
          aria-label="Novo lançamento"
        >
          <Plus size={13} strokeWidth={2.5} />
          Lançamento
        </button>
        <div
          className="hidden sm:block"
          style={{ width: 1, height: 20, background: 'oklch(from var(--color-text) l c h / 0.08)', margin: '0 4px', flexShrink: 0 }}
        />
        <button
          onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          className="btn-icon" aria-label="Alternar tema"
        >
          {theme === 'dark' ? <Sun size={16} strokeWidth={1.75} /> : <Moon size={16} strokeWidth={1.75} />}
        </button>
        <UserMenu />
      </div>
    </header>
  )
}
