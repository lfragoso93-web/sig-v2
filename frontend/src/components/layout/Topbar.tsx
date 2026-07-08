import { Sun, Moon, Menu, Plus, Briefcase, ChevronDown, CheckCircle2, Trash2 } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'
import { useAppStore } from '@/store/appStore'
import UserMenu from './UserMenu'
import { useDeletePortfolio, usePortfolios } from '@/hooks/usePortfolios'
import LogoSGI from '@/components/ui/LogoSGI'
import CreatePortfolioModal from '@/components/modals/CreatePortfolioModal'

function PortfolioSelector() {
  const { data: portfolios = [], isLoading } = usePortfolios()
  const { selectedPortfolioId, setSelectedPortfolio, clearSelectedPortfolio } = useAppStore()
  const deletePortfolio = useDeletePortfolio()
  const [open, setOpen] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  const selected = portfolios.find(p => p.id === selectedPortfolioId)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (isLoading) return

    if (!portfolios.length) {
      if (selectedPortfolioId !== null) clearSelectedPortfolio()
      return
    }

    const isValid = selectedPortfolioId !== null && portfolios.some(p => p.id === selectedPortfolioId)
    if (!isValid) {
      setSelectedPortfolio(portfolios[0].id)
    }
  }, [clearSelectedPortfolio, isLoading, portfolios, selectedPortfolioId, setSelectedPortfolio])

  const handleDelete = async (portfolioId: number, portfolioName: string) => {
    setDeleteError(null)
    const ok = window.confirm(`Excluir a carteira "${portfolioName}"? Esta ação removerá os dados vinculados a ela.`)
    if (!ok) return

    try {
      await deletePortfolio.mutateAsync(portfolioId)

      if (selectedPortfolioId === portfolioId) {
        const next = portfolios.find(p => p.id !== portfolioId)
        if (next) setSelectedPortfolio(next.id)
        else clearSelectedPortfolio()
      }
    } catch {
      setDeleteError('Não foi possível excluir a carteira. Tente novamente.')
    }
  }

  if (isLoading) {
    return (
      <div
        style={{
          width: 140,
          height: 36,
          borderRadius: 'var(--radius-lg)',
          background: 'oklch(from var(--color-text) l c h / 0.05)',
          border: '1px solid oklch(from var(--color-text) l c h / 0.09)',
        }}
      />
    )
  }

  if (!portfolios.length) {
    return (
      <>
        <button
          onClick={() => setShowCreate(true)}
          style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '0 12px', height: 36,
            borderRadius: 'var(--radius-lg)',
            border: '1px dashed oklch(from var(--color-primary) l c h / 0.4)',
            background: 'oklch(from var(--color-primary) l c h / 0.06)',
            color: 'var(--color-primary)',
            fontSize: 'var(--text-xs)', fontWeight: 560,
            cursor: 'pointer',
          }}
          aria-label="Criar carteira"
        >
          <Briefcase size={13} />
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
          onClick={() => { setDeleteError(null); setOpen(o => !o) }}
          className="flex items-center gap-2 rounded-lg transition-all"
          style={{
            padding: '0 12px', height: 36,
            background: open
              ? 'oklch(from var(--color-primary) l c h / 0.1)'
              : 'oklch(from var(--color-text) l c h / 0.05)',
            border: open
              ? '1px solid oklch(from var(--color-primary) l c h / 0.3)'
              : '1px solid oklch(from var(--color-text) l c h / 0.09)',
            color: 'var(--color-text)',
            transition: 'all 150ms cubic-bezier(0.16,1,0.3,1)',
            maxWidth: 240,
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
          <Briefcase size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
          <span className="truncate" style={{ fontSize: 'var(--text-xs)', fontWeight: 560, maxWidth: 155 }}>
            {selected?.name ?? portfolios[0]?.name ?? 'Carteira'}
          </span>
          <ChevronDown
            size={12}
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
              top: 'calc(100% + 8px)', minWidth: 240,
              background: 'var(--color-surface-2)',
              border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-lg)',
              overflow: 'hidden', padding: 7,
            }}
          >
            {portfolios.map(p => {
              const isSelected = p.id === selectedPortfolioId
              const isDeleting = deletePortfolio.isPending && deletePortfolio.variables === p.id

              return (
                <div
                  key={p.id}
                  className="flex items-center gap-1 rounded-lg transition-all"
                  style={{
                    background: isSelected
                      ? 'oklch(from var(--color-primary) l c h / 0.08)'
                      : 'transparent',
                  }}
                >
                  <button
                    onClick={() => { setSelectedPortfolio(p.id); setOpen(false) }}
                    className="flex-1 min-w-0 flex items-center justify-between rounded-lg transition-all"
                    style={{
                      padding: '8px 9px 8px 11px',
                      fontSize: 'var(--text-xs)',
                      fontWeight: isSelected ? 560 : 440,
                      color: isSelected ? 'var(--color-primary)' : 'var(--color-text)',
                      background: 'transparent',
                    }}
                    onMouseEnter={e => {
                      if (!isSelected) e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.05)'
                    }}
                    onMouseLeave={e => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent'
                    }}
                  >
                    <span className="truncate">{p.name}</span>
                    {isSelected && (
                      <CheckCircle2 size={12} style={{ color: 'var(--color-primary)', flexShrink: 0, marginLeft: 6 }} />
                    )}
                  </button>
                  <button
                    type="button"
                    disabled={isDeleting}
                    onClick={e => { e.stopPropagation(); void handleDelete(p.id, p.name) }}
                    title="Excluir carteira"
                    aria-label={`Excluir carteira ${p.name}`}
                    style={{
                      width: 28,
                      height: 28,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      borderRadius: 'var(--radius-md)',
                      border: 'none',
                      background: 'transparent',
                      color: 'var(--color-text-faint)',
                      cursor: isDeleting ? 'not-allowed' : 'pointer',
                      opacity: isDeleting ? 0.55 : 1,
                      flexShrink: 0,
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.background = 'oklch(from var(--color-notification) l c h / 0.12)'
                      e.currentTarget.style.color = 'var(--color-notification)'
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = 'transparent'
                      e.currentTarget.style.color = 'var(--color-text-faint)'
                    }}
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              )
            })}

            {deleteError && (
              <div style={{
                margin: '5px 2px', padding: '7px 8px',
                borderRadius: 'var(--radius-md)',
                background: 'oklch(from var(--color-notification) l c h / 0.1)',
                color: 'var(--color-notification)',
                fontSize: 'var(--text-xs)',
                lineHeight: 1.35,
              }}>
                {deleteError}
              </div>
            )}

            <div style={{ height: 1, background: 'oklch(from var(--color-text) l c h / 0.07)', margin: '5px 0' }} />
            <button
              onClick={() => { setOpen(false); setShowCreate(true) }}
              className="w-full flex items-center gap-2 rounded-lg"
              style={{
                padding: '8px 11px',
                fontSize: 'var(--text-xs)', fontWeight: 540,
                color: 'var(--color-primary)', background: 'transparent',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.06)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <Plus size={12} />
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
        height: 'var(--topbar-height, 58px)',
        padding: '0 clamp(1rem, 2.4vw, 1.75rem)',
        gap: 14,
        background: 'var(--color-surface)',
        borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        boxShadow: '0 1px 4px oklch(0.18 0.01 80 / 0.05)',
        position: 'relative', zIndex: 30,
      }}
    >
      <div className="flex items-center min-w-0" style={{ gap: 12 }}>
        <button onClick={toggleSidebar} className="lg:hidden btn-icon" aria-label="Abrir menu">
          <Menu size={18} />
        </button>
        <LogoSGI size={28} />
        <div
          className="hidden sm:block"
          style={{ width: 1, height: 20, background: 'oklch(from var(--color-text) l c h / 0.1)', flexShrink: 0 }}
        />
        <div className="hidden sm:block">
          <PortfolioSelector />
        </div>
      </div>

      <div className="flex items-center shrink-0" style={{ gap: 8 }}>
        <button
          onClick={() => openTransactionModal()}
          className="hidden sm:inline-flex items-center btn btn-primary"
          style={{ height: 36, padding: '0 15px', fontSize: 'var(--text-xs)', fontWeight: 620, gap: 7,
            boxShadow: '0 1px 4px oklch(from var(--color-primary) 0.3 c h / 0.45)' }}
          aria-label="Novo lançamento"
        >
          <Plus size={13} strokeWidth={2.5} />
          Lançamento
        </button>
        <div
          className="hidden sm:block"
          style={{ width: 1, height: 22, background: 'oklch(from var(--color-text) l c h / 0.08)', margin: '0 4px', flexShrink: 0 }}
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
