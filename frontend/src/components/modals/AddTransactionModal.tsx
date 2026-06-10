import { useState } from 'react'
import { X, TrendingUp, Building2, Globe, Landmark, Bitcoin, Banknote, BarChart2, CheckCircle2 } from 'lucide-react'
import { useCreateTransaction } from '@/hooks/useTransactions'
import { useAppStore } from '@/store/appStore'

interface Props {
  onClose: () => void
}

type AssetTab = {
  key: string
  label: string
  icon: React.ReactNode
  assetType: string
  currency: string
  tickerPlaceholder: string
  tickerLabel: string
  extraFields?: 'renda_fixa'
}

const TABS: AssetTab[] = [
  {
    key: 'acao',
    label: 'Ação',
    icon: <TrendingUp size={14} />,
    assetType: 'ACAO',
    currency: 'BRL',
    tickerLabel: 'Ticker',
    tickerPlaceholder: 'ex: PETR4',
  },
  {
    key: 'fii',
    label: 'FII',
    icon: <Building2 size={14} />,
    assetType: 'FII',
    currency: 'BRL',
    tickerLabel: 'Ticker',
    tickerPlaceholder: 'ex: MXRF11',
  },
  {
    key: 'etf_nacional',
    label: 'ETF BR',
    icon: <BarChart2 size={14} />,
    assetType: 'ETF_NACIONAL',
    currency: 'BRL',
    tickerLabel: 'Ticker',
    tickerPlaceholder: 'ex: BOVA11',
  },
  {
    key: 'stock',
    label: 'Stock',
    icon: <Globe size={14} />,
    assetType: 'STOCK',
    currency: 'USD',
    tickerLabel: 'Ticker',
    tickerPlaceholder: 'ex: AAPL',
  },
  {
    key: 'etf_int',
    label: 'ETF INT',
    icon: <Globe size={14} />,
    assetType: 'ETF_INTERNACIONAL',
    currency: 'USD',
    tickerLabel: 'Ticker',
    tickerPlaceholder: 'ex: VTI',
  },
  {
    key: 'tesouro',
    label: 'Tesouro',
    icon: <Landmark size={14} />,
    assetType: 'TESOURO_DIRETO',
    currency: 'BRL',
    tickerLabel: 'Código',
    tickerPlaceholder: 'ex: LTN 2029',
  },
  {
    key: 'renda_fixa',
    label: 'Renda Fixa',
    icon: <Banknote size={14} />,
    assetType: 'RENDA_FIXA',
    currency: 'BRL',
    tickerLabel: 'Código/Nome',
    tickerPlaceholder: 'ex: CDB XP 110% CDI',
    extraFields: 'renda_fixa',
  },
  {
    key: 'cripto',
    label: 'Cripto',
    icon: <Bitcoin size={14} />,
    assetType: 'CRIPTO',
    currency: 'BRL',
    tickerLabel: 'Ticker',
    tickerPlaceholder: 'ex: BTC',
  },
]

const TODAY = new Date().toISOString().split('T')[0]

export default function AddTransactionModal({ onClose }: Props) {
  const selectedPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const { mutateAsync, isPending } = useCreateTransaction()

  const [activeTab, setActiveTab] = useState<string>('acao')
  const [operation, setOperation] = useState<'buy' | 'sell'>('buy')
  const [ticker, setTicker] = useState('')
  const [quantity, setQuantity] = useState('')
  const [price, setPrice] = useState('')
  const [fees, setFees] = useState('')
  const [date, setDate] = useState(TODAY)
  const [notes, setNotes] = useState('')
  const [currency, setCurrency] = useState('BRL')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const tab = TABS.find(t => t.key === activeTab)!

  function handleTabChange(key: string) {
    const t = TABS.find(t => t.key === key)!
    setActiveTab(key)
    setCurrency(t.currency)
    setTicker('')
    setError(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!selectedPortfolioId) {
      setError('Selecione uma carteira antes de lançar.')
      return
    }
    const qty = parseFloat(quantity)
    const prc = parseFloat(price)
    const fee = parseFloat(fees || '0')
    if (!ticker.trim()) { setError('Informe o ticker/código do ativo.'); return }
    if (isNaN(qty) || qty <= 0) { setError('Quantidade deve ser maior que zero.'); return }
    if (isNaN(prc) || prc <= 0) { setError('Preço deve ser maior que zero.'); return }

    try {
      await mutateAsync({
        portfolio_id: selectedPortfolioId,
        ticker: ticker.trim().toUpperCase(),
        asset_type: tab.assetType,
        operation,
        quantity: qty,
        price: prc,
        fees: fee,
        date,
        currency,
        notes: notes.trim() || undefined,
      } as any)
      setSuccess(true)
    } catch (err: any) {
      const msg = err?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Erro ao salvar lançamento. Tente novamente.')
    }
  }

  function handleNewLancamento() {
    setSuccess(false)
    setTicker('')
    setQuantity('')
    setPrice('')
    setFees('')
    setDate(TODAY)
    setNotes('')
    setError(null)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg card shadow-xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-light-border dark:border-dark-border">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            Novo Lançamento
          </h2>
          <button onClick={onClose} className="btn-ghost p-1" aria-label="Fechar">
            <X size={16} />
          </button>
        </div>

        {/* Success state */}
        {success ? (
          <div className="flex flex-col items-center justify-center gap-4 py-12 px-6">
            <CheckCircle2 size={48} className="text-green-500" />
            <p className="text-sm font-medium text-gray-900 dark:text-gray-100">Lançamento registrado!</p>
            <div className="flex gap-3">
              <button onClick={handleNewLancamento} className="btn-primary text-xs px-4 py-1.5">
                Novo Lançamento
              </button>
              <button onClick={onClose} className="btn-secondary text-xs px-4 py-1.5">
                Fechar
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>

            {/* Asset type tabs */}
            <div className="flex overflow-x-auto scrollbar-hide px-5 pt-4 gap-1.5">
              {TABS.map(t => (
                <button
                  key={t.key}
                  type="button"
                  onClick={() => handleTabChange(t.key)}
                  className={[
                    'shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors duration-150',
                    activeTab === t.key
                      ? 'bg-brand-primary text-white'
                      : 'text-gray-500 dark:text-gray-400 hover:bg-light-100 dark:hover:bg-dark-600 hover:text-gray-800 dark:hover:text-gray-200',
                  ].join(' ')}
                >
                  {t.icon}
                  {t.label}
                </button>
              ))}
            </div>

            {/* Form body */}
            <div className="px-5 py-4 flex flex-col gap-3.5">

              {/* Operation toggle */}
              <div className="flex rounded overflow-hidden border border-light-border dark:border-dark-border text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setOperation('buy')}
                  className={[
                    'flex-1 py-2 transition-colors duration-150',
                    operation === 'buy'
                      ? 'bg-green-500 text-white'
                      : 'text-gray-500 dark:text-gray-400 hover:bg-light-100 dark:hover:bg-dark-600',
                  ].join(' ')}
                >
                  Compra
                </button>
                <button
                  type="button"
                  onClick={() => setOperation('sell')}
                  className={[
                    'flex-1 py-2 transition-colors duration-150',
                    operation === 'sell'
                      ? 'bg-red-500 text-white'
                      : 'text-gray-500 dark:text-gray-400 hover:bg-light-100 dark:hover:bg-dark-600',
                  ].join(' ')}
                >
                  Venda
                </button>
              </div>

              {/* Ticker + Currency row */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-muted mb-1">{tab.tickerLabel}</label>
                  <input
                    type="text"
                    value={ticker}
                    onChange={e => setTicker(e.target.value)}
                    placeholder={tab.tickerPlaceholder}
                    className="input w-full text-xs"
                    autoFocus
                  />
                </div>
                <div className="w-24">
                  <label className="block text-xs text-muted mb-1">Moeda</label>
                  <select
                    value={currency}
                    onChange={e => setCurrency(e.target.value)}
                    className="input w-full text-xs"
                  >
                    <option value="BRL">BRL</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="BTC">BTC</option>
                  </select>
                </div>
              </div>

              {/* Quantity + Price row */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-muted mb-1">Quantidade</label>
                  <input
                    type="number"
                    value={quantity}
                    onChange={e => setQuantity(e.target.value)}
                    placeholder="0"
                    min="0"
                    step="any"
                    className="input w-full text-xs"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-muted mb-1">
                    Preço <span className="text-gray-400">({currency})</span>
                  </label>
                  <input
                    type="number"
                    value={price}
                    onChange={e => setPrice(e.target.value)}
                    placeholder="0,00"
                    min="0"
                    step="any"
                    className="input w-full text-xs"
                  />
                </div>
              </div>

              {/* Fees + Date row */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-muted mb-1">Taxas / Corretagem</label>
                  <input
                    type="number"
                    value={fees}
                    onChange={e => setFees(e.target.value)}
                    placeholder="0,00"
                    min="0"
                    step="any"
                    className="input w-full text-xs"
                  />
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-muted mb-1">Data</label>
                  <input
                    type="date"
                    value={date}
                    onChange={e => setDate(e.target.value)}
                    className="input w-full text-xs"
                  />
                </div>
              </div>

              {/* Total preview */}
              {quantity && price && (
                <div className="rounded bg-light-50 dark:bg-dark-600 px-3 py-2 flex justify-between items-center">
                  <span className="text-xs text-muted">Total estimado</span>
                  <span className="text-xs font-semibold text-gray-900 dark:text-gray-100">
                    {currency}{' '}
                    {(parseFloat(quantity) * parseFloat(price) + parseFloat(fees || '0')).toLocaleString('pt-BR', {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </span>
                </div>
              )}

              {/* Notes */}
              <div>
                <label className="block text-xs text-muted mb-1">Observações <span className="text-gray-400">(opcional)</span></label>
                <textarea
                  value={notes}
                  onChange={e => setNotes(e.target.value)}
                  rows={2}
                  placeholder="Anotações sobre o lançamento..."
                  className="input w-full text-xs resize-none"
                />
              </div>

              {/* Error message */}
              {error && (
                <p className="text-xs text-red-500 bg-red-500/10 rounded px-3 py-2">{error}</p>
              )}

            </div>

            {/* Footer */}
            <div className="flex justify-end gap-3 px-5 py-4 border-t border-light-border dark:border-dark-border">
              <button type="button" onClick={onClose} className="btn-secondary text-xs px-4 py-1.5">
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isPending}
                className="btn-primary text-xs px-4 py-1.5 disabled:opacity-60"
              >
                {isPending ? 'Salvando...' : 'Salvar Lançamento'}
              </button>
            </div>

          </form>
        )}
      </div>
    </div>
  )
}
