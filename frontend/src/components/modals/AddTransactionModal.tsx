import { useEffect, useRef, useState } from 'react'
import {
  X, TrendingUp, Building2, Globe, Landmark,
  Bitcoin, Banknote, BarChart2, CheckCircle2, Loader2, Zap,
} from 'lucide-react'
import clsx from 'clsx'
import { useCreateTransaction } from '@/hooks/useTransactions'
import { useAppStore } from '@/store/appStore'
import { useTickerQuote } from '@/hooks/useTickerQuote'
import { useTesouroSearch, TreasuryItem } from '@/hooks/useTesouroSearch'
import { useTickerSuggest, TickerSuggestion } from '@/hooks/useTickerSuggest'

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
  extraFields?: 'renda_fixa' | 'tesouro'
  brapiEnabled?: boolean
  suggestEnabled?: boolean   // autocomplete via /assets/suggest
}

const TABS: AssetTab[] = [
  { key: 'acao',       label: 'Acao',       icon: <TrendingUp size={13} />, assetType: 'ACAO',              currency: 'BRL', tickerLabel: 'Ticker',      tickerPlaceholder: 'ex: PETR4 ou Petrobras',    brapiEnabled: true,  suggestEnabled: true  },
  { key: 'fii',        label: 'FII',        icon: <Building2  size={13} />, assetType: 'FII',               currency: 'BRL', tickerLabel: 'Ticker',      tickerPlaceholder: 'ex: MXRF11 ou Maxi Renda',  brapiEnabled: true,  suggestEnabled: true  },
  { key: 'etf_br',     label: 'ETF BR',     icon: <BarChart2  size={13} />, assetType: 'ETF_NACIONAL',      currency: 'BRL', tickerLabel: 'Ticker',      tickerPlaceholder: 'ex: BOVA11 ou IVVB11',      brapiEnabled: true,  suggestEnabled: true  },
  { key: 'stock',      label: 'Stock',      icon: <Globe      size={13} />, assetType: 'STOCK',             currency: 'USD', tickerLabel: 'Ticker',      tickerPlaceholder: 'ex: AAPL',                  brapiEnabled: true,  suggestEnabled: false },
  { key: 'etf_int',    label: 'ETF INT',    icon: <Globe      size={13} />, assetType: 'ETF_INTERNACIONAL', currency: 'USD', tickerLabel: 'Ticker',      tickerPlaceholder: 'ex: VTI',                   brapiEnabled: true,  suggestEnabled: false },
  { key: 'tesouro',    label: 'Tesouro',    icon: <Landmark   size={13} />, assetType: 'TESOURO_DIRETO',    currency: 'BRL', tickerLabel: 'Titulo',      tickerPlaceholder: 'ex: Tesouro IPCA 2029',     brapiEnabled: false, suggestEnabled: false, extraFields: 'tesouro'    },
  { key: 'renda_fixa', label: 'Renda Fixa', icon: <Banknote   size={13} />, assetType: 'RENDA_FIXA',        currency: 'BRL', tickerLabel: 'Codigo/Nome', tickerPlaceholder: 'ex: CDB XP 110% CDI',       brapiEnabled: false, suggestEnabled: false, extraFields: 'renda_fixa' },
  { key: 'cripto',     label: 'Cripto',     icon: <Bitcoin    size={13} />, assetType: 'CRIPTO',            currency: 'BRL', tickerLabel: 'Ticker',      tickerPlaceholder: 'ex: BTC',                   brapiEnabled: true,  suggestEnabled: false },
]

const RF_INDEXERS = ['CDI', 'IPCA', 'Prefixado', 'SELIC', 'IGP-M', 'Outro']
const TD_INDEXERS = ['IPCA+', 'Prefixado', 'SELIC']
const TODAY = new Date().toISOString().split('T')[0]

const inputCls = [
  'w-full rounded-md px-3 py-2 text-xs',
  'bg-surface-800 border border-surface-600',
  'text-slate-200 placeholder-slate-500',
  'focus:outline-none focus:ring-1 focus:ring-brand-500 focus:border-brand-500',
  'transition-colors duration-150',
].join(' ')

export default function AddTransactionModal({ onClose }: Props) {
  const selectedPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const { mutateAsync, isPending } = useCreateTransaction()

  const [activeTab, setActiveTab] = useState('acao')
  const [operation, setOperation] = useState<'buy' | 'sell'>('buy')
  const [ticker,    setTicker]    = useState('')
  const [assetName, setAssetName] = useState('')
  const [quantity,  setQuantity]  = useState('')
  const [price,     setPrice]     = useState('')
  const [fees,      setFees]      = useState('')
  const [date,      setDate]      = useState(TODAY)
  const [notes,     setNotes]     = useState('')
  const [currency,  setCurrency]  = useState('BRL')
  const [error,     setError]     = useState<string | null>(null)
  const [success,   setSuccess]   = useState(false)
  const [priceFromBrapi, setPriceFromBrapi] = useState(false)

  // campos extra RF / Tesouro
  const [indexer,  setIndexer]  = useState('')
  const [rate,     setRate]     = useState('')
  const [maturity, setMaturity] = useState('')
  const [issuer,   setIssuer]   = useState('')

  // dropdown states
  const [showTDSuggestions, setShowTDSuggestions] = useState(false)
  const [showRVSuggestions, setShowRVSuggestions] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const tab       = TABS.find(t => t.key === activeTab)!
  const isRF      = tab.extraFields === 'renda_fixa'
  const isTesouro = tab.extraFields === 'tesouro'
  const indexerOptions = isTesouro ? TD_INDEXERS : RF_INDEXERS

  // ── BRAPI cotacao (renda variavel) ────────────────────────────────────
  const { quote, loading: quoteLoading, error: quoteError } =
    useTickerQuote(ticker, !!tab.brapiEnabled, date)

  useEffect(() => {
    if (!quote) { setPriceFromBrapi(false); return }
    if (quote.price !== null && !price) {
      setPrice(String(quote.price))
      setPriceFromBrapi(true)
    }
    if (quote.name && !assetName) setAssetName(quote.name)
    if (quote.currency) setCurrency(quote.currency.toUpperCase())
  }, [quote])

  const prevDate = useRef(date)
  useEffect(() => {
    if (prevDate.current !== date && tab.brapiEnabled && ticker.length >= 2) {
      setPrice('')
      setPriceFromBrapi(false)
    }
    prevDate.current = date
  }, [date])

  function handlePriceChange(v: string) {
    setPrice(v)
    if (priceFromBrapi) setPriceFromBrapi(false)
  }

  // ── Tesouro Direto autocomplete ───────────────────────────────────────
  const { items: tdItems, loading: tdLoading } = useTesouroSearch(ticker, isTesouro)

  useEffect(() => {
    if (isTesouro && tdItems.length > 0) setShowTDSuggestions(true)
    else setShowTDSuggestions(false)
  }, [tdItems, isTesouro])

  // ── Renda Variavel autocomplete ───────────────────────────────────────
  const { items: rvItems, loading: rvLoading } = useTickerSuggest(ticker, !!tab.suggestEnabled)

  useEffect(() => {
    if (tab.suggestEnabled && rvItems.length > 0) setShowRVSuggestions(true)
    else setShowRVSuggestions(false)
  }, [rvItems, tab.suggestEnabled])

  // fecha dropdowns ao clicar fora
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowTDSuggestions(false)
        setShowRVSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function applyTDSuggestion(item: TreasuryItem) {
    setTicker(item.ticker)
    setAssetName(item.name)
    if (item.indexer) setIndexer(item.indexer)
    if (item.rate !== null && item.rate !== undefined) setRate(String(item.rate))
    if (item.maturity_date) setMaturity(item.maturity_date.slice(0, 10))
    if (item.price !== null && item.price !== undefined) {
      setPrice(String(item.price))
      setPriceFromBrapi(true)
    }
    setShowTDSuggestions(false)
  }

  function applyRVSuggestion(item: TickerSuggestion) {
    setTicker(item.ticker)
    setAssetName(item.name)
    setPrice('')
    setPriceFromBrapi(false)
    setShowRVSuggestions(false)
  }

  // ── handlers gerais ───────────────────────────────────────────────────
  function handleTabChange(key: string) {
    const t = TABS.find(t => t.key === key)!
    setActiveTab(key)
    setCurrency(t.currency)
    setTicker(''); setAssetName(''); setPrice('')
    setIndexer(''); setRate(''); setMaturity(''); setIssuer('')
    setPriceFromBrapi(false)
    setShowTDSuggestions(false)
    setShowRVSuggestions(false)
    setError(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!selectedPortfolioId) { setError('Selecione uma carteira antes de lancar.'); return }
    const qty = parseFloat(quantity)
    const prc = parseFloat(price)
    const fee = parseFloat(fees || '0')
    if (!ticker.trim())         { setError('Informe o ticker/codigo do ativo.'); return }
    if (isNaN(qty) || qty <= 0) { setError('Quantidade deve ser maior que zero.'); return }
    if (isNaN(prc) || prc <= 0) { setError('Preco deve ser maior que zero.'); return }
    if ((isRF || isTesouro) && !indexer) { setError('Selecione o indexador.'); return }

    let enrichedNotes = notes.trim()
    if (assetName) enrichedNotes = [assetName, enrichedNotes].filter(Boolean).join(' - ')
    if (isRF || isTesouro) {
      const extras = [
        indexer  && `Indexador: ${indexer}`,
        rate     && `Taxa: ${rate}% a.a.`,
        maturity && `Vencimento: ${maturity}`,
        isRF && issuer && `Emissor: ${issuer}`,
      ].filter(Boolean).join(' | ')
      enrichedNotes = [extras, enrichedNotes].filter(Boolean).join(' - ')
    }

    try {
      await mutateAsync({
        portfolioId: selectedPortfolioId,
        data: {
          ticker:     ticker.trim().toUpperCase(),
          asset_type: tab.assetType,
          operation,
          quantity:   qty,
          price:      prc,
          fees:       fee,
          date,
          currency,
          notes:      enrichedNotes || undefined,
        },
      })
      setSuccess(true)
    } catch (err: any) {
      const msg = err?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Erro ao salvar lancamento. Tente novamente.')
    }
  }

  function handleReset() {
    setSuccess(false)
    setTicker(''); setAssetName(''); setQuantity(''); setPrice('')
    setFees(''); setDate(TODAY); setNotes('')
    setIndexer(''); setRate(''); setMaturity(''); setIssuer('')
    setPriceFromBrapi(false)
    setShowTDSuggestions(false)
    setShowRVSuggestions(false)
    setError(null)
  }

  const total = quantity && price
    ? (parseFloat(quantity) * parseFloat(price) + parseFloat(fees || '0'))
        .toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : null

  // Componente dropdown reutilizavel
  const showDropdown = showTDSuggestions || showRVSuggestions
  const dropdownItems: Array<{ label: string; sublabel: string; onSelect: () => void }> = showTDSuggestions
    ? tdItems.map(item => ({
        label:    item.name,
        sublabel: `${item.indexer}${item.rate ? ` ${item.rate}% a.a.` : ''}${item.maturity_date ? ` • venc. ${item.maturity_date.slice(0, 7)}` : ''}`,
        onSelect: () => applyTDSuggestion(item),
      }))
    : rvItems.map(item => ({
        label:    item.ticker,
        sublabel: item.name,
        onSelect: () => applyRVSuggestion(item),
      }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      <div className="relative z-10 w-full max-w-lg rounded-xl bg-surface-900 border border-surface-700 shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-surface-700">
          <h2 className="text-sm font-semibold text-slate-100">Novo Lancamento</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-surface-700 text-slate-400 hover:text-slate-200 transition-colors" aria-label="Fechar">
            <X size={15} />
          </button>
        </div>

        {/* SUCCESS */}
        {success ? (
          <div className="flex flex-col items-center justify-center gap-4 py-14 px-6">
            <CheckCircle2 size={48} className="text-positive" />
            <p className="text-sm font-medium text-slate-100">Lancamento registrado com sucesso!</p>
            <div className="flex gap-3">
              <button onClick={handleReset} className="px-4 py-1.5 rounded-md text-xs font-medium bg-brand-600 hover:bg-brand-500 text-white transition-colors">Novo Lancamento</button>
              <button onClick={onClose}    className="px-4 py-1.5 rounded-md text-xs font-medium bg-surface-700 hover:bg-surface-600 text-slate-200 transition-colors">Fechar</button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit}>

            {/* ABAS */}
            <div className="flex overflow-x-auto px-4 pt-4 pb-2 gap-1 scrollbar-hide">
              {TABS.map(t => (
                <button key={t.key} type="button" onClick={() => handleTabChange(t.key)}
                  className={clsx(
                    'shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded text-xs font-medium transition-colors duration-150 whitespace-nowrap',
                    activeTab === t.key ? 'bg-brand-600 text-white' : 'text-slate-400 hover:bg-surface-700 hover:text-slate-200',
                  )}
                >
                  {t.icon}{t.label}
                </button>
              ))}
            </div>

            <div className="mx-4 border-t border-surface-700" />

            {/* CAMPOS */}
            <div className="px-4 py-4 flex flex-col gap-3 max-h-[70vh] overflow-y-auto">

              {/* Toggle Compra / Venda */}
              <div className="flex rounded-lg overflow-hidden border border-surface-600 text-xs font-semibold">
                <button type="button" onClick={() => setOperation('buy')}
                  className={clsx('flex-1 py-2 transition-colors duration-150', operation === 'buy' ? 'bg-positive text-white' : 'bg-surface-800 text-slate-400 hover:bg-surface-700 hover:text-slate-200')}
                >Compra</button>
                <button type="button" onClick={() => setOperation('sell')}
                  className={clsx('flex-1 py-2 transition-colors duration-150', operation === 'sell' ? 'bg-negative text-white' : 'bg-surface-800 text-slate-400 hover:bg-surface-700 hover:text-slate-200')}
                >Venda</button>
              </div>

              {/* Ticker + Moeda */}
              <div className="flex gap-3">
                <div className="flex-1" ref={dropdownRef}>
                  <label className="block text-xs text-slate-400 mb-1">{tab.tickerLabel}</label>
                  <div className="relative">
                    <input
                      type="text"
                      value={ticker}
                      onChange={e => {
                        const v = e.target.value
                        setTicker(v)
                        setAssetName('')
                        setPrice('')
                        setPriceFromBrapi(false)
                      }}
                      onFocus={() => {
                        if (showTDSuggestions || showRVSuggestions) return
                        if (isTesouro && tdItems.length > 0) setShowTDSuggestions(true)
                        if (tab.suggestEnabled && rvItems.length > 0) setShowRVSuggestions(true)
                      }}
                      placeholder={tab.tickerPlaceholder}
                      className={clsx(inputCls, 'pr-7')}
                      autoFocus
                    />
                    {(quoteLoading || tdLoading || rvLoading) && (
                      <span className="absolute right-2 top-1/2 -translate-y-1/2">
                        <Loader2 size={13} className="animate-spin text-brand-400" />
                      </span>
                    )}

                    {/* Dropdown unificado (Tesouro + RV) */}
                    {showDropdown && dropdownItems.length > 0 && (
                      <div className="absolute top-full left-0 right-0 z-50 mt-1 rounded-md border border-surface-600 bg-surface-800 shadow-xl max-h-52 overflow-y-auto">
                        {dropdownItems.map((item, i) => (
                          <button
                            key={i}
                            type="button"
                            onMouseDown={item.onSelect}
                            className="w-full text-left px-3 py-2 text-xs hover:bg-surface-700 transition-colors border-b border-surface-700 last:border-0"
                          >
                            <span className="font-medium text-slate-200">{item.label}</span>
                            {item.sublabel && (
                              <span className="ml-2 text-slate-500">{item.sublabel}</span>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  {assetName && (
                    <p className="mt-1 text-xs text-slate-500 truncate">{assetName}</p>
                  )}
                  {quoteError && !quoteLoading && (
                    <p className="mt-1 text-xs text-slate-500">{quoteError}</p>
                  )}
                </div>

                <div className="w-24">
                  <label className="block text-xs text-slate-400 mb-1">Moeda</label>
                  <select value={currency} onChange={e => setCurrency(e.target.value)} className={inputCls}>
                    <option value="BRL">BRL</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="BTC">BTC</option>
                  </select>
                </div>
              </div>

              {/* Campos extras RF / Tesouro */}
              {(isRF || isTesouro) && (
                <div className="rounded-lg border border-surface-600 bg-surface-800/50 px-3 py-3 flex flex-col gap-3">
                  <p className="text-xs font-medium text-slate-400">
                    {isTesouro ? 'Dados do Titulo' : 'Dados do Ativo'}
                  </p>
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <label className="block text-xs text-slate-400 mb-1">Indexador <span className="text-red-400">*</span></label>
                      <select value={indexer} onChange={e => setIndexer(e.target.value)} className={inputCls}>
                        <option value="">Selecionar...</option>
                        {indexerOptions.map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    </div>
                    <div className="w-32">
                      <label className="block text-xs text-slate-400 mb-1">Taxa <span className="text-slate-600">(% a.a.)</span></label>
                      <input type="number" value={rate} onChange={e => setRate(e.target.value)} placeholder={isTesouro ? 'ex: 5.82' : 'ex: 110'} min="0" step="any" className={inputCls} />
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="flex-1">
                      <label className="block text-xs text-slate-400 mb-1">Vencimento</label>
                      <input type="date" value={maturity} onChange={e => setMaturity(e.target.value)} className={inputCls} />
                    </div>
                    {isRF && (
                      <div className="flex-1">
                        <label className="block text-xs text-slate-400 mb-1">Emissor</label>
                        <input type="text" value={issuer} onChange={e => setIssuer(e.target.value)} placeholder="ex: Banco XP" className={inputCls} />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Quantidade + Preco */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-slate-400 mb-1">
                    {isRF || isTesouro ? 'Qtd / Cotas' : 'Quantidade'}
                  </label>
                  <input type="number" value={quantity} onChange={e => setQuantity(e.target.value)} placeholder="0" min="0" step="any" className={inputCls} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <label className="text-xs text-slate-400">
                      {isRF || isTesouro ? 'PU / Preco unit.' : 'Preco'}
                      <span className="text-slate-600 ml-1">({currency})</span>
                    </label>
                    {priceFromBrapi && (
                      <span className="flex items-center gap-0.5 text-[10px] font-medium text-brand-400 bg-brand-500/10 border border-brand-500/20 rounded px-1.5 py-0.5">
                        <Zap size={9} />BRAPI
                      </span>
                    )}
                  </div>
                  <input
                    type="number"
                    value={price}
                    onChange={e => handlePriceChange(e.target.value)}
                    placeholder="0,00"
                    min="0"
                    step="any"
                    className={clsx(inputCls, priceFromBrapi && 'border-brand-500/50')}
                  />
                </div>
              </div>

              {/* Taxas + Data */}
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="block text-xs text-slate-400 mb-1">Taxas / Corretagem</label>
                  <input type="number" value={fees} onChange={e => setFees(e.target.value)} placeholder="0,00" min="0" step="any" className={inputCls} />
                </div>
                <div className="flex-1">
                  <label className="block text-xs text-slate-400 mb-1">Data da operacao</label>
                  <input type="date" value={date} onChange={e => setDate(e.target.value)} className={inputCls} />
                </div>
              </div>

              {/* Total preview */}
              {total && (
                <div className="rounded-lg bg-surface-800 border border-surface-700 px-3 py-2 flex justify-between items-center">
                  <span className="text-xs text-slate-500">Total estimado</span>
                  <span className="text-xs font-semibold text-slate-100">{currency} {total}</span>
                </div>
              )}

              {/* Observacoes */}
              <div>
                <label className="block text-xs text-slate-400 mb-1">Observacoes <span className="text-slate-600">(opcional)</span></label>
                <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={2} placeholder="Anotacoes sobre o lancamento..." className={inputCls + ' resize-none'} />
              </div>

              {error && (
                <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2">{error}</p>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-end gap-2.5 px-4 py-3 border-t border-surface-700">
              <button type="button" onClick={onClose} className="px-4 py-1.5 rounded-md text-xs font-medium bg-surface-700 hover:bg-surface-600 text-slate-300 transition-colors">Cancelar</button>
              <button type="submit" disabled={isPending} className="px-4 py-1.5 rounded-md text-xs font-medium bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white transition-colors">
                {isPending ? 'Salvando...' : 'Salvar Lancamento'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
