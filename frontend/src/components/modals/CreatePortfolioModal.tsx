import { useState } from 'react'
import { X, Briefcase } from 'lucide-react'
import { useCreatePortfolio } from '@/hooks/usePortfolios'
import { useAppStore } from '@/store/appStore'

interface Props {
  onClose: () => void
}

export default function CreatePortfolioModal({ onClose }: Props) {
  const [name, setName]         = useState('')
  const [desc, setDesc]         = useState('')
  const [error, setError]       = useState('')
  const { mutateAsync, isPending } = useCreatePortfolio()
  const setSelectedPortfolioId  = useAppStore(s => s.setSelectedPortfolioId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) { setError('Informe um nome para a carteira.'); return }
    try {
      const portfolio = await mutateAsync({ name: name.trim(), description: desc.trim() || undefined })
      setSelectedPortfolioId(portfolio.id)
      onClose()
    } catch {
      setError('Erro ao criar carteira. Tente novamente.')
    }
  }

  return (
    <div
      style={{
        position:       'fixed', inset: 0, zIndex: 50,
        display:        'flex', alignItems: 'center', justifyContent: 'center',
        padding:        '1rem',
        background:     'oklch(0.12 0.01 240 / 0.7)',
        backdropFilter: 'blur(4px)',
      }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          width:        '100%', maxWidth: 420,
          background:   'var(--color-surface)',
          border:       '1px solid oklch(from var(--color-text) l c h / 0.08)',
          borderRadius: 'var(--radius-xl)',
          boxShadow:    'var(--shadow-lg)',
          overflow:     'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '1.125rem 1.5rem',
          borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{
              width: 32, height: 32, borderRadius: 'var(--radius-lg)',
              background: 'oklch(from var(--color-primary) l c h / 0.12)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Briefcase size={15} style={{ color: 'var(--color-primary)' }} />
            </div>
            <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)' }}>
              Nova Carteira
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none', border: 'none', cursor: 'pointer', padding: 4,
              color: 'var(--color-text-muted)', borderRadius: 'var(--radius-md)',
              display: 'flex', alignItems: 'center',
            }}
            aria-label="Fechar"
          >
            <X size={16} />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text)' }}>
              Nome <span style={{ color: 'var(--color-error)' }}>*</span>
            </label>
            <input
              type="text"
              value={name}
              onChange={e => { setName(e.target.value); setError('') }}
              placeholder="Ex: Carteira Principal"
              autoFocus
              style={{
                width: '100%', padding: '0.5rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: `1px solid ${error ? 'var(--color-error)' : 'oklch(from var(--color-text) l c h / 0.12)'}`,
                background: 'var(--color-surface-2)',
                color: 'var(--color-text)', fontSize: 'var(--text-sm)',
                outline: 'none', boxSizing: 'border-box',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--color-primary)')}
              onBlur={e  => (e.target.style.borderColor = error ? 'var(--color-error)' : 'oklch(from var(--color-text) l c h / 0.12)')}
            />
            {error && <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-error)' }}>{error}</p>}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
            <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text)' }}>
              Descrição <span style={{ color: 'var(--color-text-muted)', fontWeight: 400 }}>(opcional)</span>
            </label>
            <input
              type="text"
              value={desc}
              onChange={e => setDesc(e.target.value)}
              placeholder="Ex: Ações, FIIs e renda fixa"
              style={{
                width: '100%', padding: '0.5rem 0.75rem',
                borderRadius: 'var(--radius-md)',
                border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
                background: 'var(--color-surface-2)',
                color: 'var(--color-text)', fontSize: 'var(--text-sm)',
                outline: 'none', boxSizing: 'border-box',
              }}
              onFocus={e => (e.target.style.borderColor = 'var(--color-primary)')}
              onBlur={e  => (e.target.style.borderColor = 'oklch(from var(--color-text) l c h / 0.12)')}
            />
          </div>

          {/* Ações */}
          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.25rem' }}>
            <button
              type="button" onClick={onClose}
              style={{
                padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)',
                border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
                background: 'transparent', color: 'var(--color-text-muted)',
                fontSize: 'var(--text-sm)', cursor: 'pointer',
              }}
            >
              Cancelar
            </button>
            <button
              type="submit" disabled={isPending}
              style={{
                padding: '0.5rem 1.25rem', borderRadius: 'var(--radius-md)',
                border: 'none',
                background: isPending ? 'oklch(from var(--color-primary) l c h / 0.6)' : 'var(--color-primary)',
                color: 'var(--color-text-inverse)',
                fontSize: 'var(--text-sm)', fontWeight: 600,
                cursor: isPending ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', gap: '0.375rem',
              }}
            >
              {isPending ? 'Criando...' : 'Criar carteira'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
