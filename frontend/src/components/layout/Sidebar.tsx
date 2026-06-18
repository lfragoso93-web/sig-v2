import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, ArrowLeftRight, Landmark,
  Settings, Wallet, PanelLeftClose, PanelLeftOpen,
  Plus, CheckCircle2, ChevronDown, Briefcase, X,
} from 'lucide-react'
import { usePortfolios, useCreatePortfolio } from '@/hooks/usePortfolios'
import { useAppStore } from '@/store/appStore'
import { useState, useEffect } from 'react'
import Modal from '@/components/ui/Modal'

const NAV_ITEMS = [
  { to: '/carteira',                icon: LayoutDashboard, label: 'Resumo'        },
  { to: '/carteira/patrimonio',     icon: Wallet,          label: 'Patrimônio'    },
  { to: '/carteira/rentabilidade',  icon: TrendingUp,      label: 'Rentabilidade' },
  { to: '/carteira/transacoes',     icon: ArrowLeftRight,  label: 'Transações'    },
  { to: '/carteira/proventos',      icon: Landmark,        label: 'Proventos'     },
  { to: '/carteira/configuracoes',  icon: Settings,        label: 'Configurações' },
]

export default function Sidebar() {
  const { data: portfolios = [], refetch } = usePortfolios()
  const {
    selectedPortfolioId, setSelectedPortfolio,
    sidebarOpen, closeSidebar,
    sidebarCollapsed, toggleSidebarCollapsed,
  } = useAppStore()
  const createPortfolio = useCreatePortfolio()
  const navigate  = useNavigate()
  const location  = useLocation()

  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [modalOpen,    setModalOpen]    = useState(false)
  const [name,         setName]         = useState('')
  const [description,  setDescription]  = useState('')
  const [createdName,  setCreatedName]  = useState<string | null>(null)
  const [error,        setError]        = useState<string | null>(null)

  /* mobile overlay animation */
  const [mounted, setMounted] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => { closeSidebar() }, [location.pathname])
  useEffect(() => {
    document.body.style.overflow = sidebarOpen ? 'hidden' : ''
    return () => { document.body.style.overflow = '' }
  }, [sidebarOpen])
  useEffect(() => {
    if (sidebarOpen) {
      setMounted(true)
      requestAnimationFrame(() => setVisible(true))
    } else {
      setVisible(false)
      const t = setTimeout(() => setMounted(false), 260)
      return () => clearTimeout(t)
    }
  }, [sidebarOpen])

  const selected = portfolios.find(p => p.id === selectedPortfolioId)

  const handleCreate = async () => {
    if (!name.trim()) { setError('Informe um nome.'); return }
    try {
      const p = await createPortfolio.mutateAsync({ name: name.trim(), description: description.trim() || undefined })
      await refetch()
      setSelectedPortfolio(p.id)
      navigate('/carteira')
      setCreatedName(p.name)
      setTimeout(() => { setCreatedName(null); setModalOpen(false); setName(''); setDescription('') }, 1800)
    } catch { setError('Erro ao criar carteira.') }
  }

  /* — Nav Item — */
  const NavItem = ({ to, icon: Icon, label }: { to: string; icon: React.ElementType; label: string }) => (
    <NavLink
      to={to}
      end={to === '/carteira'}
      className="flex items-center rounded-lg font-medium transition-all"
      title={sidebarCollapsed ? label : undefined}
      style={({ isActive }) => ({
        padding:       sidebarCollapsed ? '9px' : '9px 12px',
        gap:           sidebarCollapsed ? 0 : 10,
        justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
        fontSize:      'var(--text-sm)',
        fontWeight:    isActive ? 560 : 440,
        background:    isActive
          ? 'oklch(from var(--color-primary) l c h / 0.11)'
          : 'transparent',
        color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
        transition: 'all 140ms cubic-bezier(0.16, 1, 0.3, 1)',
      })}
      onMouseEnter={e => {
        const el = e.currentTarget as HTMLElement
        if (!el.getAttribute('aria-current')) {
          el.style.background = 'oklch(from var(--color-text) l c h / 0.05)'
          el.style.color = 'var(--color-text)'
        }
      }}
      onMouseLeave={e => {
        const el = e.currentTarget as HTMLElement
        if (!el.getAttribute('aria-current')) {
          el.style.background = 'transparent'
          el.style.color = 'var(--color-text-muted)'
        }
      }}
    >
      <Icon size={16} strokeWidth={1.75} style={{ flexShrink: 0 }} />
      {!sidebarCollapsed && <span className="truncate">{label}</span>}
    </NavLink>
  )

  const sidebarContent = (
    <div
      className="flex flex-col h-full overflow-hidden"
      style={{
        width:       sidebarCollapsed ? 60 : 'var(--sidebar-width, 256px)',
        transition:  'width 220ms cubic-bezier(0.16, 1, 0.3, 1)',
        background:  'var(--color-surface)',
        borderRight: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        padding:     sidebarCollapsed ? '12px 6px 12px' : '12px 10px 12px',
        overflow:    'hidden',
      }}
    >
      {/* ── Seletor de carteira (mobile: visível / desktop: escondido pois fica na topbar) ── */}
      {!sidebarCollapsed && (
        <div className="lg:hidden relative mb-3">
          <button
            onClick={() => setDropdownOpen(o => !o)}
            className="w-full flex items-center justify-between rounded-xl transition-all"
            style={{
              padding:    '8px 12px',
              background: dropdownOpen
                ? 'oklch(from var(--color-primary) l c h / 0.09)'
                : 'oklch(from var(--color-text) l c h / 0.04)',
              border:     dropdownOpen
                ? '1px solid oklch(from var(--color-primary) l c h / 0.25)'
                : '1px solid oklch(from var(--color-text) l c h / 0.08)',
              color:      'var(--color-text)',
              minHeight:  38,
            }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <Briefcase size={12} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
              <span className="truncate" style={{ fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                {selected?.name ?? 'Selecionar carteira'}
              </span>
            </div>
            <ChevronDown
              size={12}
              style={{
                color:     'var(--color-text-muted)',
                flexShrink: 0,
                transform:  dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                transition: 'transform 200ms ease',
              }}
            />
          </button>

          {dropdownOpen && (
            <div
              className="absolute left-0 right-0 z-50"
              style={{
                top:          'calc(100% + 6px)',
                background:   'var(--color-surface-2)',
                border:       '1px solid oklch(from var(--color-text) l c h / 0.08)',
                borderRadius: 'var(--radius-xl)',
                boxShadow:    'var(--shadow-lg)',
                overflow:     'hidden',
                padding:       6,
              }}
            >
              {portfolios.map(p => (
                <button
                  key={p.id}
                  onClick={() => { setSelectedPortfolio(p.id); setDropdownOpen(false) }}
                  className="w-full flex items-center justify-between rounded-lg"
                  style={{
                    padding:    '7px 10px',
                    fontSize:   'var(--text-xs)',
                    fontWeight: p.id === selectedPortfolioId ? 550 : 400,
                    color:      p.id === selectedPortfolioId ? 'var(--color-primary)' : 'var(--color-text)',
                    background: p.id === selectedPortfolioId
                      ? 'oklch(from var(--color-primary) l c h / 0.08)'
                      : 'transparent',
                  }}
                  onMouseEnter={e => { if (p.id !== selectedPortfolioId) e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.05)' }}
                  onMouseLeave={e => { if (p.id !== selectedPortfolioId) e.currentTarget.style.background = 'transparent' }}
                >
                  <span className="truncate">{p.name}</span>
                  {p.id === selectedPortfolioId && <CheckCircle2 size={12} style={{ color: 'var(--color-primary)' }} />}
                </button>
              ))}
              <div style={{ borderTop: '1px solid oklch(from var(--color-text) l c h / 0.06)', paddingTop: 6, marginTop: 4 }}>
                <button
                  onClick={() => { setModalOpen(true); setDropdownOpen(false) }}
                  className="w-full flex items-center gap-2 rounded-lg"
                  style={{ padding: '7px 10px', fontSize: 'var(--text-xs)', color: 'var(--color-primary)', fontWeight: 500 }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.07)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <Plus size={12} />
                  Nova carteira
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Nav: lista única sem dividers ── */}
      <nav className="flex flex-col gap-0.5 flex-1 overflow-y-auto">
        {NAV_ITEMS.map(item => <NavItem key={item.to} {...item} />)}
      </nav>

      {/* ── Botão colapsar (desktop only) ── */}
      <button
        onClick={toggleSidebarCollapsed}
        className="hidden lg:flex items-center rounded-lg transition-all mt-2"
        style={{
          padding:        sidebarCollapsed ? '9px' : '8px 12px',
          justifyContent: sidebarCollapsed ? 'center' : 'flex-start',
          gap:            8,
          color:          'var(--color-text-faint)',
          fontSize:       'var(--text-xs)',
          fontWeight:     450,
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.05)'; e.currentTarget.style.color = 'var(--color-text-muted)' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--color-text-faint)' }}
        aria-label={sidebarCollapsed ? 'Expandir menu' : 'Recolher menu'}
        title={sidebarCollapsed ? 'Expandir menu' : 'Recolher menu'}
      >
        {sidebarCollapsed
          ? <PanelLeftOpen  size={15} strokeWidth={1.75} />
          : <>
              <PanelLeftClose size={15} strokeWidth={1.75} />
              <span className="truncate">Recolher</span>
            </>}
      </button>
    </div>
  )

  return (
    <>
      {/* Desktop */}
      <aside className="hidden lg:flex h-full">{sidebarContent}</aside>

      {/* Mobile overlay */}
      {mounted && (
        <>
          <div
            className="fixed inset-0 z-40 lg:hidden"
            style={{
              background:     'oklch(0 0 0 / 0.45)',
              backdropFilter: 'blur(4px)',
              opacity:        visible ? 1 : 0,
              transition:     'opacity 260ms ease',
            }}
            onClick={closeSidebar}
          />
          <aside
            className="fixed top-0 left-0 h-full z-50 lg:hidden flex flex-col"
            style={{
              transform:  visible ? 'translateX(0)' : 'translateX(-100%)',
              transition: 'transform 260ms cubic-bezier(0.16, 1, 0.3, 1)',
              boxShadow:  'var(--shadow-xl)',
            }}
          >
            <div style={{
              height:       'var(--topbar-height, 56px)',
              display:      'flex',
              alignItems:   'center',
              justifyContent: 'flex-end',
              padding:      '0 14px',
              borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
              background:   'var(--color-surface)',
              flexShrink:   0,
            }}>
              <button onClick={closeSidebar} className="btn-icon" aria-label="Fechar menu">
                <X size={15} />
              </button>
            </div>
            {sidebarContent}
          </aside>
        </>
      )}

      {/* Modal nova carteira */}
      {modalOpen && (
        <Modal
          title="Nova carteira"
          onClose={() => { setModalOpen(false); setName(''); setDescription(''); setError(null) }}
        >
          {createdName ? (
            <div className="flex flex-col items-center gap-3 py-4">
              <CheckCircle2 size={28} style={{ color: 'var(--color-success)' }} />
              <p style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>Carteira "{createdName}" criada!</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div>
                <label className="block mb-1.5" style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>Nome *</label>
                <input className="input" placeholder="Ex: Carteira Principal" value={name}
                  onChange={e => setName(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleCreate()} autoFocus />
              </div>
              <div>
                <label className="block mb-1.5" style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>Descrição</label>
                <input className="input" placeholder="Opcional" value={description} onChange={e => setDescription(e.target.value)} />
              </div>
              {error && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-notification)' }}>{error}</p>}
              <button onClick={handleCreate} disabled={createPortfolio.isPending} className="btn btn-primary w-full">
                {createPortfolio.isPending ? 'Criando...' : 'Criar carteira'}
              </button>
            </div>
          )}
        </Modal>
      )}
    </>
  )
}
