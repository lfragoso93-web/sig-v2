import { useState } from 'react'
import { useForm } from 'react-hook-form'
import clsx from 'clsx'
import { Search, X } from 'lucide-react'
import { TransactionCreate, TransactionType } from '@/services/transactionService'
import { useCreateTransaction } from '@/hooks/useTransactions'
import { formatBRL } from '@/utils/format'
import api from '@/services/api'

const ASSET_TYPES = [
  { value: 'ACAO_NACIONAL', label: 'Ação Nacional' },
  { value: 'FII', label: 'Fundo Imobiliário' },
  { value: 'ETF_NACIONAL', label: 'ETF Nacional' },
  { value: 'TESOURO_DIRETO', label: 'Tesouro Direto' },
  { value: 'STOCK', label: 'Stock (EUA)' },
  { value: 'ETF_INTERNACIONAL', label: 'ETF Internacional' },
  { value: 'CRIPTO', label: 'Criptomoeda' },
  { value: 'RENDA_FIXA', label: 'Renda Fixa' },
]

const TX_TYPES: { value: TransactionType; label: string; color: string }[] = [
  { value: 'COMPRA', label: 'Compra', color: 'btn-positive' },
  { value: 'VENDA', label: 'Venda', color: 'btn-negative' },
  { value: 'BONIFICACAO', label: 'Bonificação', color: 'btn-secondary' },
  { value: 'DESDOBRAMENTO', label: 'Desdobramento', color: 'btn-secondary' },
  { value: 'GRUPAMENTO', label: 'Grupamento', color: 'btn-secondary' },
]

interface Props {
  portfolioId: number
  onClose: () => void
}

export default function TransactionForm({ portfolioId, onClose }: Props) {
  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<TransactionCreate>({
    defaultValues: {
      transaction_type: 'COMPRA',
      transaction_date: new Date().toISOString().slice(0, 10),
      fees: 0,
    }
  })

  const { mutate: createTx, isPending } = useCreateTransaction(portfolioId)
  const [tickerSearch, setTickerSearch] = useState('')
  const [suggestions, setSuggestions] = useState<{ ticker: string; name: string }[]>([])
  const [loadingSearch, setLoadingSearch] = useState(false)

  const qty = watch('quantity') || 0
  const price = watch('price') || 0
  const fees = watch('fees') || 0
  const txType = watch('transaction_type')
  const total = qty * price + Number(fees)

  async function searchTicker(q: string) {
    if (q.length < 2) { setSuggestions([]); return }
    setLoadingSearch(true)
    try {
      const res = await api.get('/api/v1/assets/search', { params: { q } })
      setSuggestions(res.data)
    } catch {
      setSuggestions([])
    } finally {
      setLoadingSearch(false)
    }
  }

  function selectTicker(ticker: string, name: string) {
    setValue('ticker', ticker)
    setTickerSearch(`${ticker} — ${name}`)
    setSuggestions([])
  }

  function onSubmit(data: TransactionCreate) {
    createTx(data, { onSuccess: onClose })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5 p-1">

      {/* Tipo de transação */}
      <div>
        <label className="form-label">Tipo de operação</label>
        <div className="flex flex-wrap gap-2 mt-1">
          {TX_TYPES.map(t => (
            <button
              key={t.value}
              type="button"
              onClick={() => setValue('transaction_type', t.value)}
              className={clsx(
                'px-3 py-1.5 rounded text-xs font-medium transition-colors border',
                txType === t.value
                  ? t.value === 'COMPRA'
                    ? 'bg-positive/15 text-positive border-positive/30'
                    : t.value === 'VENDA'
                      ? 'bg-negative/15 text-negative border-negative/30'
                      : 'bg-brand-primary/15 text-brand-primary border-brand-primary/30'
                  : 'border-light-border dark:border-dark-border text-muted hover:text-gray-700 dark:hover:text-gray-300'
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
        <input type="hidden" {...register('transaction_type')} />
      </div>

      {/* Ticker + busca */}
      <div className="grid grid-cols-2 gap-3">
        <div className="relative">
          <label className="form-label">Ativo (ticker)</label>
          <div className="relative mt-1">
            <input
              type="text"
              className="input pr-8"
              placeholder="Ex: PETR4"
              value={tickerSearch}
              onChange={e => {
                setTickerSearch(e.target.value)
                setValue('ticker', e.target.value.split(' ')[0].toUpperCase())
                searchTicker(e.target.value)
              }}
            />
            <Search size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted" />
          </div>
          {suggestions.length > 0 && (
            <div className="absolute z-50 w-full mt-1 bg-white dark:bg-dark-600 border border-light-border dark:border-dark-border rounded-lg shadow-lg overflow-hidden">
              {suggestions.map(s => (
                <button
                  key={s.ticker}
                  type="button"
                  onClick={() => selectTicker(s.ticker, s.name)}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-light-100 dark:hover:bg-dark-500 transition-colors"
                >
                  <span className="font-semibold text-gray-800 dark:text-gray-200">{s.ticker}</span>
                  <span className="text-muted ml-2">{s.name}</span>
                </button>
              ))}
            </div>
          )}
          {errors.ticker && <p className="form-error">{errors.ticker.message}</p>}
          <input type="hidden" {...register('ticker', { required: 'Ticker obrigatório' })} />
        </div>

        <div>
          <label className="form-label">Tipo de ativo</label>
          <select className="input mt-1" {...register('asset_type', { required: true })}>
            {ASSET_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>
      </div>

      {/* Data, Qtd, Preço, Corretagem */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <label className="form-label">Data</label>
          <input type="date" className="input mt-1" {...register('transaction_date', { required: true })} />
        </div>
        <div>
          <label className="form-label">Quantidade</label>
          <input type="number" step="0.00000001" min="0" className="input mt-1"
            placeholder="100"
            {...register('quantity', { required: true, valueAsNumber: true, min: 0.00000001 })} />
          {errors.quantity && <p className="form-error">Obrigatório</p>}
        </div>
        <div>
          <label className="form-label">Preço unitário (R$)</label>
          <input type="number" step="0.01" min="0" className="input mt-1"
            placeholder="28.50"
            {...register('price', { required: true, valueAsNumber: true, min: 0.01 })} />
          {errors.price && <p className="form-error">Obrigatório</p>}
        </div>
        <div>
          <label className="form-label">Corretagem (R$)</label>
          <input type="number" step="0.01" min="0" className="input mt-1"
            placeholder="0.00"
            {...register('fees', { valueAsNumber: true })} />
        </div>
      </div>

      {/* Corretora + Notas */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="form-label">Corretora</label>
          <input type="text" className="input mt-1" placeholder="XP, Rico, Clear…" {...register('broker')} />
        </div>
        <div>
          <label className="form-label">Observações</label>
          <input type="text" className="input mt-1" placeholder="Opcional" {...register('notes')} />
        </div>
      </div>

      {/* Total calculado */}
      {total > 0 && (
        <div className="rounded-lg bg-light-100 dark:bg-dark-700 px-4 py-3 flex items-center justify-between">
          <span className="text-xs text-muted">Total da operação</span>
          <span className={clsx(
            'text-base font-bold tabular-nums',
            txType === 'VENDA' ? 'text-positive' : 'text-gray-900 dark:text-gray-100'
          )}>
            {txType === 'VENDA' ? '+' : ''}{formatBRL(total)}
          </span>
        </div>
      )}

      {/* Botões */}
      <div className="flex justify-end gap-2 pt-1">
        <button type="button" onClick={onClose} className="btn-secondary px-4 py-2 text-sm">
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isPending}
          className={clsx(
            'px-4 py-2 text-sm font-medium rounded transition-colors',
            txType === 'COMPRA'
              ? 'bg-positive text-white hover:bg-positive/90'
              : txType === 'VENDA'
                ? 'bg-negative text-white hover:bg-negative/90'
                : 'btn-primary'
          )}
        >
          {isPending ? 'Salvando…' : `Registrar ${TX_TYPES.find(t => t.value === txType)?.label}`}
        </button>
      </div>
    </form>
  )
}
