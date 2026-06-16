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
      requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))
    } else {
      setVisible(false)
      const t = setTimeout(() => setMounted(false), 280)
      return () => clearTimeout(t)
    }
  }, [sidebarOpen])

  const selected = portfolios.find(p => p.id === selectedPortfolioId)

  function openModal() {
    setName('')
    setDescription('')
    setCreatedName(null)
    setError(null)
    setDropdownOpen(false)
    setModalOpen(true)
  }

  function handleClose() {
    setModalOpen(false)
    setCreatedName(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    setError(null)
    try {
      const created = await createPortfolio.mutateAsync({
        name: name.trim(),
        description: description.trim() || undefined,
      })
      setSelectedPortfolio(created.id)
      setCreatedName(created.name)
      await refetch()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      let msg: string
      if (Array.isArray(detail)) {
        msg = detail.map((e: any) => e.msg ?? JSON.stringify(e)).join(', ')
      } else if (typeof detail === 'string') {
        msg = detail
      } else if (detail) {
        msg = JSON.stringify(detail)
      } else {
        msg = 'Erro ao criar carteira. Tente novamente.'
      }
      setError(msg)
    }
  }

  function handleCreateAnother() {
    setName('')
    setDescription('')
    setCreatedName(null)
    setError(null)
  }

  function handleGoToResumo() {
    handleClose()
    navigate('/carteira')
  }

  const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
    background: isActive ? 'oklch(from var(--color-primary) l c h / 0.1)' : 'transparent',
    color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
  })

  const navLinkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
      isActive ? 'font-semibold' : 'font-normal'
    }`

  const sidebarContent = (
    <aside
      className="flex flex-col h-full shrink-0 border-r py-5"
      style={{
        width:       'var(--sidebar-width, 240px)',
        background:  'var(--color-surface)',
        borderColor: 'var(--color-divider)',
      }}
    >
      {/* Logo + botão fechar (mobile) */}
      <div className="px-5 mb-5 flex items-center justify-between">
        <span className="text-base font-bold tracking-tight" style={{ color: 'var(--color-primary)' }}>
          SIG
          <span className="text-xs font-medium ml-1" style={{ color: 'var(--color-text-muted)' }}>v2</span>
        </span>
        <button
          onClick={closeSidebar}
          className="lg:hidden flex items-center justify-center p-1 rounded-md transition-colors"
          style={{ color: 'var(--color-text-muted)', minWidth: 32, minHeight: 32 }}
          aria-label="Fechar menu"
        >
          <X size={16} />
        </button>
      </div>

      {/* Seletor de carteira */}
      <div className="px-3 mb-4 relative">
        <button
          onClick={() => setDropdownOpen(o => !o)}
          className="w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-sm border transition-colors"
          style={{
            background:  'var(--color-surface-offset)',
            borderColor: 'var(--color-border)',
            color:       'var(--color-text)',
            minHeight:   40,
          }}
        >
          <div className="flex items-center gap-2 min-w-0">
            <Briefcase size={14} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
            <span className="truncate text-sm font-medium">
              {selected?.name ?? 'Selecionar carteira'}
            </span>
          </div>
          <ChevronDown
            size={14}
            style={{
              color: 'var(--color-text-muted)',
              flexShrink: 0,
              transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              transition: 'transform 180ms ease',
            }}
          />
        </button>

        {dropdownOpen && (
          <div
            className="absolute left-3 right-3 mt-1 rounded-lg border overflow-hidden z-10"
            style={{
              background:  'var(--color-surface-2)',
              borderColor: 'var(--color-border)',
              boxShadow:   'var(--shadow-md)',
            }}
          >
            {portfolios.length === 0 ? (
              <p className="px-3 py-3 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Nenhuma carteira cadastrada.
              </p>
            ) : (
              portfolios.map(p => (
                <button
                  key={p.id}
                  onClick={() => { setSelectedPortfolio(p.id); setDropdownOpen(false) }}
                  className="w-full text-left px-3 py-2.5 text-sm transition-colors"
                  style={{
                    background: selectedPortfolioId === p.id
                      ? 'oklch(from var(--color-primary) l c h / 0.1)'
                      : 'transparent',
                    color: selectedPortfolioId === p.id
                      ? 'var(--color-primary)'
                      : 'var(--color-text)',
                    fontWeight: selectedPortfolioId === p.id ? 600 : 400,
                  }}
                >
                  {p.name}
                </button>
              ))
            )}
            <div style={{ borderTop: '1px solid var(--color-divider)' }}>
              <button
                onClick={openModal}
                className="w-full text-left px-3 py-2.5 text-sm flex items-center gap-2 transition-colors"
                style={{ color: 'var(--color-primary)', fontWeight: 500 }}
              >
                <Plus size={13} /> Nova carteira
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Divisor */}
      <div className="mx-3 mb-3" style={{ borderTop: '1px solid var(--color-divider)' }} />

      {/* Nav */}
      <nav className="flex flex-col gap-0.5 px-3 flex-1">
        {NAV_TOP.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} end={to === '/carteira'} className={navLinkClass} style={navLinkStyle}>
            <Icon size={16} />
            {label}
          </NavLink>
        ))}

        <div className="my-1" style={{ borderTop: '1px solid var(--color-divider)' }} />

        {NAV_BOTTOM.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} className={navLinkClass} style={navLinkStyle}>
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  )

  return (
    <>
      {/* Desktop: sidebar fixa (≥1024px) */}
      <div className="hidden lg:flex h-full">
        {sidebarContent}
      </div>

      {/* Mobile/Tablet: drawer overlay (<1024px) com animação */}
      {mounted && (
        <div
          className="lg:hidden fixed inset-0 z-40 flex"
          style={{
            transition: 'opacity 280ms ease',
            opacity: visible ? 1 : 0,
          }}
        >
          <div
            className="absolute inset-0"
            style={{ background: 'rgba(0,0,0,0.5)' }}
            onClick={closeSidebar}
            aria-label="Fechar menu"
          />
          <div
            className="relative z-50 h-full flex"
            style={{
              transform: visible ? 'translateX(0)' : 'translateX(-100%)',
              transition: 'transform 280ms cubic-bezier(0.4,0,0.2,1)',
            }}
          >
            {sidebarContent}
          </div>
        </div>
      )}

      {/* Modal Nova Carteira */}
      <Modal open={modalOpen} onClose={handleClose} title="Nova carteira" size="sm">
        {createdName ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            gap: 'var(--space-4)', textAlign: 'center', padding: 'var(--space-4) 0',
          }}>
            <CheckCircle2 size={48} style={{ color: 'var(--color-success)' }} />
            <div>
              <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
                Carteira criada com sucesso!
              </p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: 0, marginTop: '4px' }}>
                <strong style={{ color: 'var(--color-primary)' }}>{createdName}</strong> está pronta para uso.
              </p>
            </div>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: 0 }}>
              O que deseja fazer agora?
            </p>
            <div style={{ display: 'flex', gap: 'var(--space-3)', width: '100%' }}>
              <button
                type="button"
                onClick={handleCreateAnother}
                style={{
                  flex: 1, padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface-offset)',
                  color: 'var(--color-text)',
                  fontSize: 'var(--text-xs)', fontWeight: 500, cursor: 'pointer',
                }}
              >
                Criar outra
              </button>
              <button
                type="button"
                onClick={handleGoToResumo}
                style={{
                  flex: 1, padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: 'none',
                  background: 'var(--color-primary)',
                  color: 'var(--color-text-inverse)',
                  fontSize: 'var(--text-xs)', fontWeight: 500, cursor: 'pointer',
                }}
              >
                Ir ao Resumo
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text)' }}>
                Nome <span style={{ color: 'var(--color-error)' }}>*</span>
              </label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Ex: Carteira Principal"
                required
                autoFocus
                style={{
                  width: '100%',
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface-2)',
                  color: 'var(--color-text)',
                  fontSize: '16px',
                  outline: 'none',
                }}
                onFocus={e => (e.target.style.borderColor = 'var(--color-primary)')}
                onBlur={e  => (e.target.style.borderColor = 'var(--color-border)')}
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
              <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>
                Descrição <span style={{ color: 'var(--color-text-faint)' }}>(opcional)</span>
              </label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                placeholder="Ex: Foco em FIIs e ações pagadoras de dividendos"
                rows={3}
                style={{
                  width: '100%',
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface-2)',
                  color: 'var(--color-text)',
                  fontSize: '16px',
                  resize: 'vertical',
                  outline: 'none',
                  fontFamily: 'inherit',
                }}
                onFocus={e => (e.target.style.borderColor = 'var(--color-primary)')}
                onBlur={e  => (e.target.style.borderColor = 'var(--color-border)')}
              />
            </div>
            {error && (
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-error)', margin: 0 }}>
                {error}
              </p>
            )}
            <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={handleClose}
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface-offset)',
                  color: 'var(--color-text)',
                  fontSize: 'var(--text-xs)', fontWeight: 500, cursor: 'pointer',
                }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={createPortfolio.isPending || !name.trim()}
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  borderRadius: 'var(--radius-md)',
                  border: 'none',
                  background: (createPortfolio.isPending || !name.trim())
                    ? 'var(--color-primary-highlight)'
                    : 'var(--color-primary)',
                  color: 'var(--color-text-inverse)',
                  fontSize: 'var(--text-xs)', fontWeight: 500,
                  cursor: (createPortfolio.isPending || !name.trim()) ? 'not-allowed' : 'pointer',
                }}
              >
                {createPortfolio.isPending ? 'Criando...' : 'Criar carteira'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </>
  )
}
