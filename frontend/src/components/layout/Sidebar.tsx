import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, ArrowLeftRight, Landmark,
  Settings, Briefcase, Plus, CheckCircle2, ChevronDown, Wallet, X,
} from 'lucide-react'
import { usePortfolios, useCreatePortfolio } from '@/hooks/usePortfolios'
import { useAppStore } from '@/store/appStore'
import { useState, useEffect } from 'react'
import Modal from '@/components/ui/Modal'
import LogoSGI from '@/components/ui/LogoSGI'

const NAV_MAIN = [
  { to: '/carteira',            icon: LayoutDashboard, label: 'Resumo'     },
  { to: '/carteira/patrimonio', icon: Wallet,          label: 'Patrimônio' },
]
const NAV_ANALYTICS = [
  { to: '/carteira/rentabilidade', icon: TrendingUp,     label: 'Rentabilidade' },
  { to: '/carteira/transacoes',    icon: ArrowLeftRight, label: 'Transações'    },
  { to: '/carteira/proventos',     icon: Landmark,       label: 'Proventos'     },
]
const NAV_SYSTEM = [
  { to: '/carteira/configuracoes', icon: Settings, label: 'Configurações' },
]

export default function Sidebar() {
  const { data: portfolios = [], refetch } = usePortfolios()
  const { selectedPortfolioId, setSelectedPortfolio, sidebarOpen, closeSidebar } = useAppStore()
  const createPortfolio = useCreatePortfolio()
  const navigate = useNavigate()
  const location = useLocation()

  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [modalOpen,    setModalOpen]    = useState(false)
  const [name,         setName]         = useState('')
  const [description,  setDescription]  = useState('')
  const [createdName,  setCreatedName]  = useState<string | null>(null)
  const [error,        setError]        = useState<string | null>(null)
  const [mounted,      setMounted]      = useState(false)
  const [visible,      setVisible]      = useState(false)

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

  /* — Item de navegação — */
  const NavItem = ({ to, icon: Icon, label }: { to: string; icon: React.ElementType; label: string }) => (
    <NavLink
      to={to}
      end={to === '/carteira'}
      className="flex items-center gap-3 rounded-lg font-medium transition-all"
      style={({ isActive }) => ({
        padding:         '9px 14px',
        fontSize:        'var(--text-sm)',
        fontWeight:      isActive ? 550 : 450,
        letterSpacing:   isActive ? '-0.005em' : '0',
        background:      isActive
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
      <span className="truncate">{label}</span>
    </NavLink>
  )

  /* — Label de seção — */
  const SectionLabel = ({ children }: { children: React.ReactNode }) => (
    <p style={{
      fontSize:      '0.68rem',
      fontWeight:    600,
      letterSpacing: '0.08em',
      textTransform: 'uppercase',
      color:         'var(--color-text-faint)',
      padding:       '0 14px',
      marginBottom:  2,
      marginTop:     14,
      userSelect:    'none',
    }}>{children}</p>
  )

  const Divider = () => (
    <div style={{
      height:     1,
      margin:     '8px 14px',
      background: 'oklch(from var(--color-text) l c h / 0.07)',
    }} />
  )

  const sidebarContent = (
    <div
      className="flex flex-col h-full overflow-y-auto"
      style={{
        width:       'var(--sidebar-width, 256px)',
        background:  'var(--color-surface)',
        borderRight: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        padding:     '18px 10px 20px',
      }}
    >
      {/* ── Header ──────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between"
        style={{ padding: '0 4px', marginBottom: 20 }}
      >
        <LogoSGI size={28} />
        <button
          onClick={closeSidebar}
          className="lg:hidden btn-icon"
          aria-label="Fechar menu"
        >
          <X size={15} />
        </button>
      </div>

      {/* ── Seletor de carteira ───────────────────────────── */}
      <div className="relative" style={{ marginBottom: 14 }}>
        <button
          onClick={() => setDropdownOpen(o => !o)}
          className="w-full flex items-center justify-between rounded-xl transition-all"
          style={{
            padding:    '10px 14px',
            background: dropdownOpen
              ? 'oklch(from var(--color-primary) l c h / 0.09)'
              : 'oklch(from var(--color-text) l c h / 0.04)',
            border:     dropdownOpen
              ? '1px solid oklch(from var(--color-primary) l c h / 0.25)'
              : '1px solid oklch(from var(--color-text) l c h / 0.08)',
            color:      'var(--color-text)',
            minHeight:  40,
            transition: 'all 150ms cubic-bezier(0.16, 1, 0.3, 1)',
          }}
          onMouseEnter={e => {
            if (!dropdownOpen) {
              e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.07)'
              e.currentTarget.style.borderColor = 'oklch(from var(--color-text) l c h / 0.12)'
            }
          }}
          onMouseLeave={e => {
            if (!dropdownOpen) {
              e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.04)'
              e.currentTarget.style.borderColor = 'oklch(from var(--color-text) l c h / 0.08)'
            }
          }}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <Briefcase size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
            <span className="truncate" style={{ fontSize: 'var(--text-sm)', fontWeight: 500 }}>
              {selected?.name ?? 'Selecionar carteira'}
            </span>
          </div>
          <ChevronDown
            size={13}
            style={{
              color:      'var(--color-text-muted)',
              flexShrink: 0,
              transform:  dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 200ms cubic-bezier(0.16, 1, 0.3, 1)',
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
            }}
          >
            <div style={{ padding: 6 }}>
              {portfolios.map(p => (
                <button
                  key={p.id}
                  onClick={() => { setSelectedPortfolio(p.id); setDropdownOpen(false) }}
                  className="w-full flex items-center justify-between rounded-lg transition-all"
                  style={{
                    padding:    '8px 12px',
                    fontSize:   'var(--text-sm)',
                    fontWeight: p.id === selectedPortfolioId ? 500 : 400,
                    color:      p.id === selectedPortfolioId ? 'var(--color-primary)' : 'var(--color-text)',
                    background: p.id === selectedPortfolioId
                      ? 'oklch(from var(--color-primary) l c h / 0.08)'
                      : 'transparent',
                    transition: 'all 120ms ease',
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
                    <CheckCircle2 size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
                  )}
                </button>
              ))}
            </div>
            <div style={{
              borderTop: '1px solid oklch(from var(--color-text) l c h / 0.06)',
              padding: 6,
            }}>
              <button
                onClick={() => { setModalOpen(true); setDropdownOpen(false) }}
                className="w-full flex items-center gap-2 rounded-lg transition-all"
                style={{
                  padding:  '8px 12px',
                  fontSize: 'var(--text-sm)',
                  color:    'var(--color-primary)',
                  fontWeight: 500,
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.07)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <Plus size={13} />
                Nova carteira
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Navegação ──────────────────────────────────────────── */}
      <nav className="flex flex-col gap-0.5 flex-1">
        <SectionLabel>Carteira</SectionLabel>
        {NAV_MAIN.map(item => <NavItem key={item.to} {...item} />)}

        <Divider />

        <SectionLabel>Análise</SectionLabel>
        {NAV_ANALYTICS.map(item => <NavItem key={item.to} {...item} />)}

        <div className="flex-1" />

        <Divider />

        {NAV_SYSTEM.map(item => <NavItem key={item.to} {...item} />)}
      </nav>
    </div>
  )

  return (
    <>
      <aside className="hidden lg:flex h-full">{sidebarContent}</aside>

      {mounted && (
        <>
          <div
            className="fixed inset-0 z-40 lg:hidden"
            style={{
              background: 'oklch(0 0 0 / 0.45)',
              backdropFilter: 'blur(4px)',
              opacity:    visible ? 1 : 0,
              transition: 'opacity 260ms ease',
            }}
            onClick={closeSidebar}
          />
          <aside
            className="fixed top-0 left-0 h-full z-50 lg:hidden"
            style={{
              transform:  visible ? 'translateX(0)' : 'translateX(-100%)',
              transition: 'transform 260ms cubic-bezier(0.16, 1, 0.3, 1)',
              boxShadow:  'var(--shadow-xl)',
            }}
          >
            {sidebarContent}
          </aside>
        </>
      )}

      {modalOpen && (
        <Modal
          title="Nova carteira"
          onClose={() => { setModalOpen(false); setName(''); setDescription(''); setError(null) }}
        >
          {createdName ? (
            <div className="flex flex-col items-center gap-3 py-4">
              <CheckCircle2 size={28} style={{ color: 'var(--color-success)' }} />
              <p style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--color-text)' }}>
                Carteira "{createdName}" criada!
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div>
                <label className="block mb-1.5" style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>Nome *</label>
                <input
                  className="input"
                  placeholder="Ex: Carteira Principal"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleCreate()}
                  autoFocus
                />
              </div>
              <div>
                <label className="block mb-1.5" style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>Descrição</label>
                <input
                  className="input"
                  placeholder="Opcional"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                />
              </div>
              {error && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-notification)' }}>{error}</p>}
              <button
                onClick={handleCreate}
                disabled={createPortfolio.isPending}
                className="btn btn-primary w-full"
              >
                {createPortfolio.isPending ? 'Criando...' : 'Criar carteira'}
              </button>
            </div>
          )}
        </Modal>
      )}
    </>
  )
}
