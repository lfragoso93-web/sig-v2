import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { useCreateTransaction } from '@/hooks/useTransactions'

const ASSET_TYPES = [
  'Acao Nacional', 'FII', 'ETF Nacional', 'Tesouro Direto',
  'Stock', 'ETF Internacional', 'Criptomoeda', 'Renda Fixa',
]

interface Props {
  portfolioId: number
  onClose: () => void
}

export default function ModalNovaTransacao({ portfolioId, onClose }: Props) {
  const createTx = useCreateTransaction()
  const today = new Date().toISOString().split('T')[0]

  const [form, setForm] = useState({
    ticker: '', asset_type: 'Acao Nacional',
    operation: 'buy' as 'buy' | 'sell',
    quantity: '', price: '', fees: '',
    date: today, notes: '',
  })
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = '' }
  }, [])

  function set(field: string, value: string) {
    setForm(f => ({ ...f, [field]: value }))
  }

  const qty   = parseFloat(form.quantity) || 0
  const price = parseFloat(form.price)    || 0
  const fees  = parseFloat(form.fees)     || 0
  const total = form.operation === 'buy' ? qty * price + fees : qty * price - fees

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!form.ticker.trim()) { setError('Informe o ticker do ativo.'); return }
    if (qty <= 0)             { setError('Quantidade deve ser maior que zero.'); return }
    if (price <= 0)           { setError('Preco deve ser maior que zero.'); return }
    try {
      await createTx.mutateAsync({
        portfolioId,
        data: {
          ticker:     form.ticker.toUpperCase().trim(),
          asset_type: form.asset_type,
          operation:  form.operation,
          quantity:   qty, price, fees: fees || 0,
          date:       form.date,
          notes:      form.notes || undefined,
        },
      })
      onClose()
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (Array.isArray(detail)) setError(detail.map((d: any) => d.msg ?? JSON.stringify(d)).join(', '))
      else if (typeof detail === 'string') setError(detail)
      else setError('Erro ao registrar transacao. Verifique os dados e tente novamente.')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-end md:items-center md:justify-center px-0 md:px-4"
      style={{ background: 'oklch(0 0 0 / 0.45)' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        className={[
          'w-full flex flex-col',
          'rounded-t-2xl max-h-[92dvh]',
          'md:rounded-xl md:max-w-lg md:max-h-[90vh]',
        ].join(' ')}
        style={{
          background:  'var(--color-surface)',
          borderTop:   '1px solid var(--color-border)',
          boxShadow:   'var(--shadow-lg)',
        }}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex justify-center pt-3 pb-1 md:hidden">
          <div className="w-10 h-1 rounded-full" style={{ background: 'var(--color-text-faint)' }} />
        </div>

        <div className="flex items-center justify-between px-5 py-4 border-b shrink-0" style={{ borderColor: 'var(--color-divider)' }}>
          <h2 className="text-base font-semibold">Nova transacao</h2>
          <button className="btn btn-ghost p-1.5 rounded" onClick={onClose} aria-label="Fechar">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto px-5 py-5 flex flex-col gap-4">
          <div className="flex gap-2">
            {(['buy', 'sell'] as const).map(op => (
              <button
                key={op} type="button" onClick={() => set('operation', op)}
                className="flex-1 py-2.5 rounded-lg text-sm font-semibold border transition-colors"
                style={{
                  background: form.operation === op
                    ? op === 'buy'
                      ? 'oklch(from var(--color-success) l c h / 0.15)'
                      : 'oklch(from var(--color-notification) l c h / 0.15)'
                    : 'var(--color-surface-offset)',
                  color: form.operation === op
                    ? op === 'buy' ? 'var(--color-success)' : 'var(--color-notification)'
                    : 'var(--color-text-muted)',
                  borderColor: form.operation === op
                    ? op === 'buy' ? 'var(--color-success)' : 'var(--color-notification)'
                    : 'var(--color-border)',
                  minHeight: 44,
                }}
              >
                {op === 'buy' ? '\u25b2 Compra' : '\u25bc Venda'}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Ticker <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input className="input uppercase" placeholder="Ex: PETR4" value={form.ticker} onChange={e => set('ticker', e.target.value)} autoCapitalize="characters" style={{ fontSize: 16 }} required />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Tipo de ativo</label>
              <select className="input text-sm" value={form.asset_type} onChange={e => set('asset_type', e.target.value)} style={{ fontSize: 16 }}>
                {ASSET_TYPES.map(t => <option key={t}>{t}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Quantidade <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input type="number" min="0" step="any" className="input" placeholder="0" value={form.quantity} onChange={e => set('quantity', e.target.value)} inputMode="decimal" style={{ fontSize: 16 }} required />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Preco unit. <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input type="number" min="0" step="any" className="input" placeholder="0,00" value={form.price} onChange={e => set('price', e.target.value)} inputMode="decimal" style={{ fontSize: 16 }} required />
            </div>
            <div className="flex flex-col gap-1.5 col-span-2 md:col-span-1">
              <label className="text-sm font-medium">Taxas</label>
              <input type="number" min="0" step="any" className="input" placeholder="0,00" value={form.fees} onChange={e => set('fees', e.target.value)} inputMode="decimal" style={{ fontSize: 16 }} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Data <span style={{ color: 'var(--color-error)' }}>*</span></label>
              <input type="date" className="input" value={form.date} onChange={e => set('date', e.target.value)} style={{ fontSize: 16 }} required />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-sm font-medium">Observacao</label>
              <input className="input" placeholder="Opcional" value={form.notes} onChange={e => set('notes', e.target.value)} style={{ fontSize: 16 }} />
            </div>
          </div>

          <div className="flex items-center justify-between px-4 py-3 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
            <span className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Total da operacao</span>
            <span className="text-base font-bold tabular-nums">
              {total > 0 ? new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(total) : 'R$ 0,00'}
            </span>
          </div>

          {error && (
            <p className="text-sm rounded px-3 py-2" style={{ color: 'var(--color-notification)', background: 'oklch(from var(--color-notification) l c h / 0.1)' }}>
              {error}
            </p>
          )}

          <div className="flex gap-2 pt-1 pb-safe">
            <button type="button" className="flex-1 md:flex-none btn btn-secondary" onClick={onClose} disabled={createTx.isPending}>Cancelar</button>
            <button type="submit" className="flex-1 md:flex-none btn btn-primary" disabled={createTx.isPending} style={{ minHeight: 44 }}>
              {createTx.isPending ? 'Salvando...' : 'Registrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
