import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  TrendingUp,
  ArrowLeftRight,
  Landmark,
  Settings,
  ChevronDown,
  Briefcase,
  Plus,
  CheckCircle2,
  Wallet,
  TrendingDown,
  Building2,
  Banknote,
} from 'lucide-react'
import { usePortfolios, useCreatePortfolio } from '@/hooks/usePortfolios'
import { useAppStore } from '@/store/appStore'
import { useState, useEffect } from 'react'
import Modal from '@/components/ui/Modal'

const NAV_TOP = [
  { to: '/carteira',                  icon: LayoutDashboard,  label: 'Resumo'        },
]

const NAV_PATRIMONIO_SUBS = [
  { to: '/carteira/patrimonio/renda-variavel', icon: TrendingDown, label: 'Renda Variável' },
  { to: '/carteira/patrimonio/tesouro',        icon: Building2,    label: 'Tesouro Direto' },
  { to: '/carteira/patrimonio/renda-fixa',     icon: Banknote,     label: 'Renda Fixa'     },
]

const NAV_BOTTOM = [
  { to: '/carteira/rentabilidade',    icon: TrendingUp,        label: 'Rentabilidade' },
  { to: '/carteira/transacoes',       icon: ArrowLeftRight,    label: 'Transações'    },
  { to: '/carteira/proventos',        icon: Landmark,          label: 'Proventos'     },
  { to: '/carteira/configuracoes',    icon: Settings,          label: 'Configurações' },
]

export default function Sidebar() {
  const { data: portfolios = [], refetch } = usePortfolios()
  const { selectedPortfolioId, setSelectedPortfolio } = useAppStore()
  const createPortfolio = useCreatePortfolio()
  const navigate = useNavigate()
  const location = useLocation()

  const [dropdownOpen, setDropdownOpen]   = useState(false)
  const [modalOpen, setModalOpen]         = useState(false)
  const [name, setName]                   = useState('')
  const [description, setDescription]    = useState('')
  const [createdName, setCreatedName]     = useState<string | null>(null)
  const [error, setError]                 = useState<string | null>(null)

  // Abre submenu automaticamente se estiver em qualquer rota de patrimônio
  const isPatrimonioActive = location.pathname.startsWith('/carteira/patrimonio')
  const [patrimonioOpen, setPatrimonioOpen] = useState(isPatrimonioActive)

  useEffect(() => {
    if (isPatrimonioActive) setPatrimonioOpen(true)
  }, [isPatrimonioActive])

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

  return (
    <>
      <aside
        className="flex flex-col h-full w-56 shrink-0 border-r py-5"
        style={{
          background:  'var(--color-surface)',
          borderColor: 'var(--color-divider)',
        }}
      >
        {/* Logo */}
        <div className="px-5 mb-6">
          <span className="text-base font-bold tracking-tight" style={{ color: 'var(--color-primary)' }}>
            SIG
            <span className="text-xs font-medium ml-1" style={{ color: 'var(--color-text-muted)' }}>v2</span>
          </span>
        </div>

        {/* Seletor de carteira */}
        <div className="px-3 mb-4">
          <button
            onClick={() => setDropdownOpen(o => !o)}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm border transition-colors"
            style={{
              background:  'var(--color-surface-offset)',
              borderColor: 'var(--color-border)',
              color:       'var(--color-text)',
            }}
          >
            <div className="flex items-center gap-2 min-w-0">
              <Briefcase size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
              <span className="truncate text-xs font-medium">
                {selected?.name ?? 'Selecionar carteira'}
              </span>
            </div>
            <ChevronDown
              size={13}
              style={{
                flexShrink: 0,
                transition: 'transform var(--transition-interactive)',
                transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              }}
            />
          </button>

          {dropdownOpen && (
            <div
              className="mt-1 rounded-lg border overflow-hidden"
              style={{
                background:  'var(--color-surface-2)',
                borderColor: 'var(--color-border)',
                boxShadow:   'var(--shadow-md)',
              }}
            >
              {portfolios.map(p => (
                <button
                  key={p.id}
                  onClick={() => { setSelectedPortfolio(p.id); setDropdownOpen(false) }}
                  className="w-full text-left px-3 py-2 text-xs transition-colors"
                  style={{
                    background: selectedPortfolioId === p.id
                      ? 'oklch(from var(--color-primary) l c h / 0.1)'
                      : 'transparent',
                    color:      selectedPortfolioId === p.id
                      ? 'var(--color-primary)'
                      : 'var(--color-text)',
                    fontWeight: selectedPortfolioId === p.id ? 600 : 400,
                  }}
                >
                  {p.name}
                </button>
              ))}
              <div style={{ borderTop: '1px solid var(--color-divider)' }}>
                <button
                  onClick={openModal}
                  className="w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors"
                  style={{ color: 'var(--color-primary)', fontWeight: 500 }}
                >
                  <Plus size={12} /> Nova carteira
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-0.5 px-3 flex-1">
          {/* Resumo */}
          {NAV_TOP.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={navLinkClass}
              style={navLinkStyle}
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}

          {/* ── Patrimônio (com submenu) ── */}
          <div>
            {/* Botão pai: navega E expande */}
            <button
              onClick={() => {
                navigate('/carteira/patrimonio')
                setPatrimonioOpen(o => !o)
              }}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors"
              style={{
                background: isPatrimonioActive
                  ? 'oklch(from var(--color-primary) l c h / 0.1)'
                  : 'transparent',
                color: isPatrimonioActive
                  ? 'var(--color-primary)'
                  : 'var(--color-text-muted)',
                fontWeight: isPatrimonioActive ? 600 : 400,
              }}
            >
              <span className="flex items-center gap-2.5">
                <Wallet size={15} />
                Patrimônio
              </span>
              <ChevronDown
                size={13}
                style={{
                  transition: 'transform var(--transition-interactive)',
                  transform: patrimonioOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                  flexShrink: 0,
                }}
              />
            </button>

            {/* Subitens */}
            {patrimonioOpen && (
              <div className="flex flex-col gap-0.5 mt-0.5 ml-3 pl-3" style={{ borderLeft: '1px solid var(--color-divider)' }}>
                {NAV_PATRIMONIO_SUBS.map(({ to, icon: Icon, label }) => (
                  <NavLink
                    key={to}
                    to={to}
                    className={navLinkClass}
                    style={navLinkStyle}
                  >
                    <Icon size={14} />
                    <span className="text-xs">{label}</span>
                  </NavLink>
                ))}
              </div>
            )}
          </div>

          {/* Demais itens */}
          {NAV_BOTTOM.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={navLinkClass}
              style={navLinkStyle}
            >
              <Icon size={15} />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

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
                  fontSize: 'var(--text-sm)',
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
                  fontSize: 'var(--text-sm)',
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
