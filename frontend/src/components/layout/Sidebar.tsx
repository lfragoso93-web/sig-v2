import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  TrendingUp,
  ArrowLeftRight,
  Landmark,
  Settings,
  Briefcase,
  Plus,
  CheckCircle2,
  ChevronDown,
  Wallet,
  X,
} from 'lucide-react'
import { usePortfolios, useCreatePortfolio } from '@/hooks/usePortfolios'
import { useAppStore } from '@/store/appStore'
import { useState, useEffect } from 'react'
import Modal from '@/components/ui/Modal'
import LogoSGI from '@/components/ui/LogoSGI'

const NAV_TOP = [
  { to: '/carteira',            icon: LayoutDashboard, label: 'Resumo'     },
  { to: '/carteira/patrimonio', icon: Wallet,           label: 'Patrimônio' },
]

const NAV_BOTTOM = [
  { to: '/carteira/rentabilidade', icon: TrendingUp,     label: 'Rentabilidade' },
  { to: '/carteira/transacoes',    icon: ArrowLeftRight, label: 'Transações'    },
  { to: '/carteira/proventos',     icon: Landmark,       label: 'Proventos'     },
  { to: '/carteira/configuracoes', icon: Settings,       label: 'Configurações' },
]

export default function Sidebar() {
  const { data: portfolios = [], refetch } = usePortfolios()
  const { selectedPortfolioId, setSelectedPortfolio, sidebarOpen, closeSidebar } = useAppStore()
  const createPortfolio = useCreatePortfolio()
  const navigate = useNavigate()
  const location = useLocation()

  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [modalOpen, setModalOpen]       = useState(false)
  const [name, setName]                 = useState('')
  const [description, setDescription]   = useState('')
  const [createdName, setCreatedName]   = useState<string | null>(null)
  const [error, setError]               = useState<string | null>(null)

  const [mounted, setMounted] = useState(false)
  const [visible, setVisible] = useState(false)

  useEffect(() => { closeSidebar() }, [location.pathname])

  useEffect(() => {
    if (sidebarOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
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
    } catch {
      setError('Erro ao criar carteira.')
    }
  }

  const navLink = (to: string, Icon: React.ElementType, label: string) => (
    <NavLink
      key={to}
      to={to}
      end={to === '/carteira'}
      className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150"
      style={({ isActive }) => ({
        background: isActive ? 'oklch(from var(--color-primary) l c h / 0.1)' : 'transparent',
        color:      isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
      })}
    >
      <Icon size={15} />
      {label}
    </NavLink>
  )

  const sidebarContent = (
    <div
      className="flex flex-col h-full"
      style={{
        width: 220,
        background: 'var(--color-surface)',
        borderRight: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        padding: '16px 8px',
      }}
    >
      {/* ── Logo + fechar mobile ───────────────────────────────── */}
      <div className="flex items-center justify-between px-2 mb-5">
        <LogoSGI size={24} />
        <button
          onClick={closeSidebar}
          className="lg:hidden flex items-center justify-center rounded-lg transition-colors"
          style={{ color: 'var(--color-text-muted)', width: 28, height: 28 }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          aria-label="Fechar menu"
        >
          <X size={15} />
        </button>
      </div>

      {/* ── Seletor de carteira ───────────────────────────────── */}
      <div className="px-1 mb-3 relative">
        <button
          onClick={() => setDropdownOpen(o => !o)}
          className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors"
          style={{
            background:  'var(--color-surface-offset)',
            border:      '1px solid oklch(from var(--color-text) l c h / 0.08)',
            color:       'var(--color-text)',
            minHeight:   36,
          }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Briefcase size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
            <span className="truncate text-sm font-medium">
              {selected?.name ?? 'Selecionar carteira'}
            </span>
          </div>
          <ChevronDown
            size={13}
            style={{
              color: 'var(--color-text-muted)',
              transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 150ms ease',
              flexShrink: 0,
            }}
          />
        </button>

        {/* Dropdown carteiras */}
        {dropdownOpen && (
          <div
            className="absolute left-1 right-1 mt-1 rounded-lg overflow-hidden z-50"
            style={{
              background: 'var(--color-surface-2)',
              border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
              boxShadow: 'var(--shadow-md)',
            }}
          >
            {portfolios.map(p => (
              <button
                key={p.id}
                onClick={() => { setSelectedPortfolio(p.id); setDropdownOpen(false) }}
                className="w-full flex items-center justify-between px-3 py-2 text-sm transition-colors"
                style={{
                  color: 'var(--color-text)',
                  background: p.id === selectedPortfolioId ? 'oklch(from var(--color-primary) l c h / 0.08)' : 'transparent',
                }}
                onMouseEnter={e => { if (p.id !== selectedPortfolioId) e.currentTarget.style.background = 'var(--color-surface-offset)' }}
                onMouseLeave={e => { if (p.id !== selectedPortfolioId) e.currentTarget.style.background = 'transparent' }}
              >
                <span className="truncate">{p.name}</span>
                {p.id === selectedPortfolioId && (
                  <CheckCircle2 size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
                )}
              </button>
            ))}
            <div style={{ borderTop: '1px solid oklch(from var(--color-text) l c h / 0.06)', margin: '2px 0' }} />
            <button
              onClick={() => { setModalOpen(true); setDropdownOpen(false) }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm transition-colors"
              style={{ color: 'var(--color-primary)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.06)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <Plus size={13} />
              Nova carteira
            </button>
          </div>
        )}
      </div>

      {/* ── Nav principal ───────────────────────────────────── */}
      <nav className="flex flex-col gap-0.5">
        {NAV_TOP.map(({ to, icon, label }) => navLink(to, icon, label))}
      </nav>

      <div
        style={{
          margin: '12px 12px',
          height: 1,
          background: 'oklch(from var(--color-text) l c h / 0.06)',
        }}
      />

      <nav className="flex flex-col gap-0.5">
        {NAV_BOTTOM.map(({ to, icon, label }) => navLink(to, icon, label))}
      </nav>
    </div>
  )

  return (
    <>
      {/* Desktop: sidebar fixa */}
      <aside className="hidden lg:flex h-full">
        {sidebarContent}
      </aside>

      {/* Mobile: overlay + drawer */}
      {mounted && (
        <>
          <div
            className="fixed inset-0 z-40 lg:hidden"
            style={{
              background: 'oklch(0 0 0 / 0.45)',
              opacity: visible ? 1 : 0,
              transition: 'opacity 250ms ease',
            }}
            onClick={closeSidebar}
          />
          <aside
            className="fixed top-0 left-0 h-full z-50 lg:hidden"
            style={{
              transform: visible ? 'translateX(0)' : 'translateX(-100%)',
              transition: 'transform 250ms cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
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
              <CheckCircle2 size={32} style={{ color: 'var(--color-success)' }} />
              <p className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
                Carteira “{createdName}” criada!
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Nome *</label>
                <input
                  className="input w-full"
                  placeholder="Minha carteira"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleCreate()}
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-1" style={{ color: 'var(--color-text-muted)' }}>Descrição</label>
                <input
                  className="input w-full"
                  placeholder="Opcional"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                />
              </div>
              {error && <p className="text-xs" style={{ color: 'var(--color-notification)' }}>{error}</p>}
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
