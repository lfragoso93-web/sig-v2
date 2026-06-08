import { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'

interface Props {
  onClose: () => void
  onConfirm: (name: string, description: string) => Promise<void>
  loading: boolean
}

export default function ModalNovaCarteira({ onClose, onConfirm, loading }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Foco automático e trap de tecla Escape
  useEffect(() => {
    inputRef.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) return
    await onConfirm(name.trim(), description.trim())
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'oklch(0 0 0 / 0.45)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="w-full max-w-md rounded-xl border shadow-xl p-6"
        style={{
          background: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          boxShadow: 'var(--shadow-lg)',
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold">Nova carteira</h2>
          <button
            onClick={onClose}
            className="btn btn-ghost p-1 rounded"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="cart-name" className="text-sm font-medium">Nome <span className="text-red-500">*</span></label>
            <input
              ref={inputRef}
              id="cart-name"
              className="input"
              placeholder="Ex: Carteira de dividendos"
              value={name}
              onChange={e => setName(e.target.value)}
              maxLength={60}
              required
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="cart-desc" className="text-sm font-medium">Descrição <span style={{ color: 'var(--color-text-muted)' }}>(opcional)</span></label>
            <textarea
              id="cart-desc"
              className="input resize-none"
              placeholder="Ex: Foco em FIIs e ações pagadoras de dividendos"
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={3}
              maxLength={200}
            />
          </div>

          <div className="flex justify-end gap-2 mt-1">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading || !name.trim()}>
              {loading ? 'Criando...' : 'Criar carteira'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
