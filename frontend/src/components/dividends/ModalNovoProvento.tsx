import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useCreateDividend } from '@/hooks/useDividends'

const ASSET_TYPES = [
  'Acao Nacional', 'FII', 'ETF Nacional', 'Tesouro Direto',
  'Stock', 'ETF Internacional', 'Criptomoeda', 'Renda Fixa',
]

const DIVIDEND_TYPES = [
  { value: 'dividendo',   label: 'Dividendo'   },
  { value: 'jcp',         label: 'JCP'         },
  { value: 'rendimento',  label: 'Rendimento'  },
  { value: 'amortizacao', label: 'Amortização' },
  { value: 'outro',       label: 'Outro'       },
]

interface Props {
  portfolioId: number
  onClose: () => void
}

export default function ModalNovoProvento({ portfolioId, onClose }: Props) {
  const createDiv = useCreateDividend(portfolioId)
  const today = new Date().toISOString().split('T')[0]

  const [form, setForm] = useState({
    ticker:       '',
    asset_type:   'FII',
    type:         'dividendo',
    amount:       '',   // valor por cota
    quantity:     '',   // quantidade de cotas
    payment_date: today,
    ex_date:      '',
  })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  function set(field: string, value: string) {
    setForm(f => ({ ...f, [field]: value }))
  }

  const amount   = parseFloat(form.amount)   || 0
  const quantity = parseFloat(form.quantity) || 0
  const total    = amount * quantity

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)

    if (!form.ticker.trim()) { setError('Informe o ticker do ativo.'); return }
    if (amount   <= 0)       { setError('Valor por cota deve ser maior que zero.'); return }
    if (quantity <= 0)       { setError('Quantidade deve ser maior que zero.'); return }

    try {
      await createDiv.mutateAsync({
        ticker:       form.ticker.toUpperCase().trim(),
        asset_type:   form.asset_type,
        type:         form.type as any,
        amount,
        quantity,
        payment_date: form.payment_date,
        ex_date:      form.ex_date || null,
      })
      onClose()
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Erro ao registrar provento.')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'oklch(0 0 0 / 0.45)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className="w-full max-w-lg rounded-xl border shadow-xl"
        style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', boxShadow: 'var(--shadow-lg)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b" style={{ borderColor: 'var(--color-divider)' }}>
          <h2 className="text-base font-semibold">Lançar provento</h2>
          <button className="btn btn-ghost p-1 rounded" onClick={onClose} aria-label="Fechar"><X size={18} /></button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 flex flex-col gap-4">

          {/* Ticker + Tipo de ativo */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Ticker <span className="text-red-500">*</span></label>
              <input
                className="input uppercase"
                placeholder="Ex: MXRF11"
                value={form.ticker}
                onChange={e => set('ticker', e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Tipo de ativo</label>
              <select className="input text-sm" value={form.asset_type} onChange={e => set('asset_type', e.target.value)}>
                {ASSET_TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
          </div>

          {/* Tipo de provento */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Tipo de provento</label>
            <div className="flex flex-wrap gap-2">
              {DIVIDEND_TYPES.map(dt => (
                <button
                  key={dt.value}
                  type="button"
                  onClick={() => set('type', dt.value)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors"
                  style={{
                    background: form.type === dt.value
                      ? 'oklch(from var(--color-gold) l c h / 0.15)'
                      : 'var(--color-surface-offset)',
                    color: form.type === dt.value ? 'var(--color-gold)' : 'var(--color-text-muted)',
                    borderColor: form.type === dt.value ? 'var(--color-gold)' : 'var(--color-border)',
                  }}
                >
                  {dt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Valor/cota + Quantidade */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Valor por cota (R$) <span className="text-red-500">*</span></label>
              <input
                type="number" min="0" step="any"
                className="input"
                placeholder="0,00"
                value={form.amount}
                onChange={e => set('amount', e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Quantidade de cotas <span className="text-red-500">*</span></label>
              <input
                type="number" min="0" step="any"
                className="input"
                placeholder="0"
                value={form.quantity}
                onChange={e => set('quantity', e.target.value)}
                required
              />
            </div>
          </div>

          {/* Datas */}
          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Data de pagamento <span className="text-red-500">*</span></label>
              <input
                type="date" className="input"
                value={form.payment_date}
                onChange={e => set('payment_date', e.target.value)}
                required
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Data com <span style={{ color: 'var(--color-text-muted)' }}>(opcional)</span></label>
              <input
                type="date" className="input"
                value={form.ex_date}
                onChange={e => set('ex_date', e.target.value)}
              />
            </div>
          </div>

          {/* Total */}
          <div
            className="flex items-center justify-between px-4 py-3 rounded-lg"
            style={{ background: 'var(--color-surface-offset)' }}
          >
            <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Total recebido</span>
            <span className="text-base font-bold tabular-nums" style={{ color: 'var(--color-gold)' }}>
              {total > 0
                ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(total)
                : 'R$ 0,00'}
            </span>
          </div>

          {error && (
            <p className="text-sm rounded px-3 py-2"
              style={{ color: 'var(--color-notification)', background: 'oklch(from var(--color-notification) l c h / 0.1)' }}>
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-1">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={createDiv.isPending}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={createDiv.isPending}>
              {createDiv.isPending ? 'Salvando...' : 'Lançar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
