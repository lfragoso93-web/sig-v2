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

const secLabel: React.CSSProperties = {
  fontSize: '0.65rem', fontWeight: 600, letterSpacing: '0.08em',
  textTransform: 'uppercase', color: 'var(--color-text-faint)',
  padding: '0 10px', marginBottom: 2, marginTop: 10, userSelect: 'none',
}

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
      const t = setTimeout(() => setMounted(false), 250)
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

  const NavItem = ({ to, icon: Icon, label }: { to: string; icon: React.ElementType; label: string }) => (
    <NavLink
      to={to} end={to === '/carteira'}
      className="flex items-center gap-2.5 rounded-lg font-medium transition-all duration-150"
      style={({ isActive }) => ({
        padding: '7px 10px', fontSize: '0.8125rem',
        background: isActive ? 'oklch(from var(--color-primary) l c h / 0.1)' : 'transparent',
        color:      isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
      })}
      onMouseEnter={e => {
        const el = e.currentTarget as HTMLElement
        if (!el.getAttribute('aria-current')) {
          el.style.background = 'var(--color-surface-offset)'
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
      <Icon size={14} strokeWidth={1.75} style={{ flexShrink: 0 }} />
      <span className="truncate">{label}</span>
    </NavLink>
  )

  const Divider = () => (
    <div style={{ height: 1, margin: '4px 10px', background: 'oklch(from var(--color-text) l c h / 0.06)' }} />
  )

  const sidebarContent = (
    <div className="flex flex-col h-full overflow-y-auto"
      style={{ width: 228, background: 'var(--color-surface)', borderRight: '1px solid oklch(from var(--color-text) l c h / 0.07)', padding: '14px 8px 16px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between" style={{ padding: '0 4px', marginBottom: 16 }}>
        <LogoSGI size={24} />
        <button onClick={closeSidebar} className="lg:hidden flex items-center justify-center rounded-lg"
          style={{ color: 'var(--color-text-faint)', width: 26, height: 26 }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-text-muted)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-faint)')}
          aria-label="Fechar menu"
        ><X size={14} /></button>
      </div>

      {/* Seletor de carteira */}
      <div className="relative" style={{ marginBottom: 10 }}>
        <button onClick={() => setDropdownOpen(o => !o)}
          className="w-full flex items-center justify-between rounded-lg transition-colors duration-150"
          style={{
            padding: '7px 10px',
            background: dropdownOpen ? 'var(--color-surface-offset)' : 'oklch(from var(--color-text) l c h / 0.04)',
            border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
            color: 'var(--color-text)', minHeight: 34,
          }}
          onMouseEnter={e => { if (!dropdownOpen) e.currentTarget.style.background = 'var(--color-surface-offset)' }}
          onMouseLeave={e => { if (!dropdownOpen) e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.04)' }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Briefcase size={12} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
            <span className="truncate" style={{ fontSize: '0.8rem', fontWeight: 500 }}>{selected?.name ?? 'Selecionar carteira'}</span>
          </div>
          <ChevronDown size={12} style={{ color: 'var(--color-text-faint)', flexShrink: 0, transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 150ms ease' }} />
        </button>

        {dropdownOpen && (
          <div className="absolute left-0 right-0 z-50"
            style={{ top: 'calc(100% + 4px)', background: 'var(--color-surface)', border: '1px solid oklch(from var(--color-text) l c h / 0.09)', borderRadius: 10, boxShadow: 'var(--shadow-md)', overflow: 'hidden' }}
          >
            <div style={{ padding: 4 }}>
              {portfolios.map(p => (
                <button key={p.id} onClick={() => { setSelectedPortfolio(p.id); setDropdownOpen(false) }}
                  className="w-full flex items-center justify-between rounded-md transition-colors"
                  style={{ padding: '6px 8px', fontSize: '0.8rem', color: 'var(--color-text)', background: p.id === selectedPortfolioId ? 'oklch(from var(--color-primary) l c h / 0.09)' : 'transparent' }}
                  onMouseEnter={e => { if (p.id !== selectedPortfolioId) e.currentTarget.style.background = 'var(--color-surface-offset)' }}
                  onMouseLeave={e => { if (p.id !== selectedPortfolioId) e.currentTarget.style.background = 'transparent' }}
                >
                  <span className="truncate">{p.name}</span>
                  {p.id === selectedPortfolioId && <CheckCircle2 size={12} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />}
                </button>
              ))}
            </div>
            <div style={{ borderTop: '1px solid oklch(from var(--color-text) l c h / 0.06)', padding: 4 }}>
              <button onClick={() => { setModalOpen(true); setDropdownOpen(false) }}
                className="w-full flex items-center gap-2 rounded-md transition-colors"
                style={{ padding: '6px 8px', fontSize: '0.8rem', color: 'var(--color-primary)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.07)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              ><Plus size={12} />Nova carteira</button>
            </div>
          </div>
        )}
      </div>

      {/* Navegacao */}
      <nav className="flex flex-col gap-px flex-1">
        <p style={secLabel}>Carteira</p>
        {NAV_MAIN.map(item => <NavItem key={item.to} {...item} />)}

        <Divider />

        <p style={secLabel}>Análise</p>
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
          <div className="fixed inset-0 z-40 lg:hidden"
            style={{ background: 'oklch(0 0 0 / 0.4)', opacity: visible ? 1 : 0, transition: 'opacity 250ms ease' }}
            onClick={closeSidebar}
          />
          <aside className="fixed top-0 left-0 h-full z-50 lg:hidden"
            style={{ transform: visible ? 'translateX(0)' : 'translateX(-100%)', transition: 'transform 250ms cubic-bezier(0.16, 1, 0.3, 1)' }}
          >{sidebarContent}</aside>
        </>
      )}

      {modalOpen && (
        <Modal title="Nova carteira" onClose={() => { setModalOpen(false); setName(''); setDescription(''); setError(null) }}>
          {createdName ? (
            <div className="flex flex-col items-center gap-3 py-4">
              <CheckCircle2 size={28} style={{ color: 'var(--color-success)' }} />
              <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>Carteira "{createdName}" criada!</p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>Nome *</label>
                <input className="input w-full" placeholder="Ex: Carteira Principal" value={name}
                  onChange={e => setName(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleCreate()} autoFocus />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--color-text-muted)' }}>Descrição</label>
                <input className="input w-full" placeholder="Opcional" value={description} onChange={e => setDescription(e.target.value)} />
              </div>
              {error && <p className="text-xs" style={{ color: 'var(--color-notification)' }}>{error}</p>}
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
