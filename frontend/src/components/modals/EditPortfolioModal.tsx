import { useState } from 'react'
import { Briefcase, X } from 'lucide-react'
import { Portfolio, useUpdatePortfolio } from '@/hooks/usePortfolios'

interface Props {
  portfolio: Portfolio
  onClose: () => void
}

export default function EditPortfolioModal({ portfolio, onClose }: Props) {
  const [name, setName] = useState(portfolio.name)
  const [description, setDescription] = useState(portfolio.description ?? '')
  const [error, setError] = useState('')
  const updatePortfolio = useUpdatePortfolio()

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    const normalizedName = name.trim()
    if (!normalizedName) {
      setError('Informe um nome para a carteira.')
      return
    }

    try {
      await updatePortfolio.mutateAsync({
        id: portfolio.id,
        name: normalizedName,
        description: description.trim() || undefined,
      })
      onClose()
    } catch {
      setError('Não foi possível atualizar a carteira. Tente novamente.')
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 60,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '1rem', background: 'oklch(0.12 0.01 240 / 0.7)',
        backdropFilter: 'blur(4px)',
      }}
      onClick={event => { if (event.target === event.currentTarget) onClose() }}
    >
      <div style={{
        width: '100%', maxWidth: 420,
        background: 'var(--color-surface)',
        border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
        borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-lg)', overflow: 'hidden',
      }}>
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
              Editar carteira
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar"
            style={{
              background: 'none', border: 'none', cursor: 'pointer', padding: 4,
              color: 'var(--color-text-muted)', borderRadius: 'var(--radius-md)',
              display: 'flex', alignItems: 'center',
            }}
          >
            <X size={16} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', fontSize: 'var(--text-xs)', color: 'var(--color-text)' }}>
            Nome
            <input
              type="text"
              value={name}
              maxLength={120}
              autoFocus
              onChange={event => { setName(event.target.value); setError('') }}
              style={{
                width: '100%', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-md)',
                border: `1px solid ${error ? 'var(--color-error)' : 'oklch(from var(--color-text) l c h / 0.12)'}`,
                background: 'var(--color-surface-2)', color: 'var(--color-text)',
                fontSize: 'var(--text-sm)', outline: 'none', boxSizing: 'border-box',
              }}
            />
          </label>

          <label style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem', fontSize: 'var(--text-xs)', color: 'var(--color-text)' }}>
            Descrição
            <input
              type="text"
              value={description}
              onChange={event => setDescription(event.target.value)}
              style={{
                width: '100%', padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-md)',
                border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
                background: 'var(--color-surface-2)', color: 'var(--color-text)',
                fontSize: 'var(--text-sm)', outline: 'none', boxSizing: 'border-box',
              }}
            />
          </label>

          {error && <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-error)' }}>{error}</p>}

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '0.25rem' }}>
            <button
              type="button"
              onClick={onClose}
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
              type="submit"
              disabled={updatePortfolio.isPending}
              style={{
                padding: '0.5rem 1.25rem', borderRadius: 'var(--radius-md)', border: 'none',
                background: updatePortfolio.isPending
                  ? 'oklch(from var(--color-primary) l c h / 0.6)'
                  : 'var(--color-primary)',
                color: 'var(--color-text-inverse)', fontSize: 'var(--text-sm)', fontWeight: 600,
                cursor: updatePortfolio.isPending ? 'not-allowed' : 'pointer',
              }}
            >
              {updatePortfolio.isPending ? 'Salvando...' : 'Salvar alterações'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
