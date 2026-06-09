import { NavLink, useNavigate } from 'react-router-dom'
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
} from 'lucide-react'
import { usePortfolios, useCreatePortfolio } from '@/hooks/usePortfolios'
import { useAppStore } from '@/store/appStore'
import { useState } from 'react'
import Modal from '@/components/ui/Modal'

const NAV = [
  { to: '/app/dashboard',      icon: LayoutDashboard,  label: 'Resumo'       },
  { to: '/app/rentabilidade',  icon: TrendingUp,        label: 'Rentabilidade'},
  { to: '/app/transacoes',     icon: ArrowLeftRight,    label: 'Transações'   },
  { to: '/app/proventos',      icon: Landmark,          label: 'Proventos'    },
  { to: '/app/configuracoes',  icon: Settings,           label: 'Configurações'},
]

export default function Sidebar() {
  const { data: portfolios = [], refetch } = usePortfolios()
  const { selectedPortfolioId, setSelectedPortfolio } = useAppStore()
  const createPortfolio = useCreatePortfolio()
  const navigate = useNavigate()

  const [dropdownOpen, setDropdownOpen] = useState(false)
  const [modalOpen, setModalOpen]       = useState(false)
  const [name, setName]                 = useState('')
  const [description, setDescription]  = useState('')
  const [createdName, setCreatedName]   = useState<string | null>(null)
  const [error, setError]               = useState<string | null>(null)

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
      const created = await createPortfolio.mutateAsync({ name: name.trim(), description: description.trim() || undefined })
      setSelectedPortfolio(created.id)
      setCreatedName(created.name)
      await refetch()
    } catch {
      setError('Erro ao criar carteira. Tente novamente.')
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
    navigate('/app/dashboard')
  }

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
            <ChevronDown size={13} className={`transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} style={{ flexShrink: 0 }} />
          </button>

          {dropdownOpen && (
            <div
              className="mt-1 rounded-lg border overflow-hidden"
              style={{ background: 'var(--color-surface-2)', borderColor: 'var(--color-border)', boxShadow: 'var(--shadow-md)' }}
            >
              {portfolios.map(p => (
                <button
                  key={p.id}
                  onClick={() => { setSelectedPortfolio(p.id); setDropdownOpen(false) }}
                  className="w-full text-left px-3 py-2 text-xs transition-colors"
                  style={{
                    background: selectedPortfolioId === p.id ? 'oklch(from var(--color-primary) l c h / 0.1)' : 'transparent',
                    color:      selectedPortfolioId === p.id ? 'var(--color-primary)' : 'var(--color-text)',
                    fontWeight: selectedPortfolioId === p.id ? 600 : 400,
                  }}
                >
                  {p.name}
                </button>
              ))}

              {/* Divider + Criar nova */}
              <div style={{ borderTop: '1px solid var(--color-divider)' }}>
                <button
                  onClick={openModal}
                  className="w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors"
                  style={{ color: 'var(--color-primary)', fontWeight: 500 }}
                >
                  <Plus size={12} />
                  Nova carteira
                </button>
              </div>
            </div>
          )}

          {/* Botão quando não há carteiras */}
          {portfolios.length === 0 && (
            <button
              onClick={openModal}
              className="mt-1 w-full flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border transition-colors"
              style={{
                background:  'oklch(from var(--color-primary) l c h / 0.08)',
                borderColor: 'oklch(from var(--color-primary) l c h / 0.3)',
                color:       'var(--color-primary)',
              }}
            >
              <Plus size={12} />
              Nova carteira
            </button>
          )}
        </div>

        {/* Nav */}
        <nav className="flex flex-col gap-0.5 px-3 flex-1">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? 'font-semibold' : 'font-normal'
                }`
              }
              style={({ isActive }) => ({
                background: isActive ? 'oklch(from var(--color-primary) l c h / 0.1)' : 'transparent',
                color:      isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
              })}
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
          /* === Tela de sucesso === */
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-4)', textAlign: 'center', padding: 'var(--space-4) 0' }}>
            <CheckCircle2 size={48} style={{ color: 'var(--color-success)' }} />
            <div>
              <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', marginBottom: 'var(--space-1)' }}>
                Carteira criada com sucesso!
              </p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                <strong style={{ color: 'var(--color-primary)' }}>{createdName}</strong> está pronta para uso.
              </p>
            </div>
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
              O que deseja fazer agora?
            </p>
            <div style={{ display: 'flex', gap: 'var(--space-3)', width: '100%' }}>
              <button
                onClick={handleCreateAnother}
                style={{
                  flex: 1,
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface-offset)',
                  color: 'var(--color-text)',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'background var(--transition-interactive)',
                }}
              >
                Criar outra
              </button>
              <button
                onClick={handleGoToResumo}
                style={{
                  flex: 1,
                  padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  border: 'none',
                  background: 'var(--color-primary)',
                  color: 'var(--color-text-inverse)',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'background var(--transition-interactive)',
                }}
              >
                Ir ao Resumo
              </button>
            </div>
          </div>
        ) : (
          /* === Formulário === */
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
                  transition: 'border-color var(--transition-interactive)',
                }}
                onFocus={e => (e.target.style.borderColor = 'var(--color-primary)')}
                onBlur={e => (e.target.style.borderColor = 'var(--color-border)')}
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
                  transition: 'border-color var(--transition-interactive)',
                  fontFamily: 'inherit',
                }}
                onFocus={e => (e.target.style.borderColor = 'var(--color-primary)')}
                onBlur={e => (e.target.style.borderColor = 'var(--color-border)')}
              />
            </div>

            {error && (
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-error)', margin: 0 }}>{error}</p>
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
                  fontSize: 'var(--text-xs)',
                  fontWeight: 500,
                  cursor: 'pointer',
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
                  background: createPortfolio.isPending || !name.trim() ? 'var(--color-primary-highlight)' : 'var(--color-primary)',
                  color: 'var(--color-text-inverse)',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 500,
                  cursor: createPortfolio.isPending || !name.trim() ? 'not-allowed' : 'pointer',
                  transition: 'background var(--transition-interactive)',
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
