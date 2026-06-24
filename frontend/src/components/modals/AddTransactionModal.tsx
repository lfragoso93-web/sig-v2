import { useEffect, useRef, useState } from 'react'
import {
  X, TrendingUp, Building2, Globe, Landmark,
  Bitcoin, Banknote, BarChart2, CheckCircle2, Loader2, Zap, ArrowDownCircle, ArrowUpCircle, Globe2,
} from 'lucide-react'
import { useCreateTransaction, useUpdateTransaction } from '@/hooks/useTransactions'
import { useAppStore } from '@/store/appStore'
import { useTickerQuote } from '@/hooks/useTickerQuote'
import { useTesouroSearch, TreasuryItem } from '@/hooks/useTesouroSearch'
import { useTickerSuggest, TickerSuggestion } from '@/hooks/useTickerSuggest'
import { useTreasuryPrice } from '@/hooks/useTreasuryPrice'

interface Props { onClose: () => void }

type AssetTab = {
  key: string; label: string; icon: React.ReactNode
  assetType: string; currency: string
  tickerPlaceholder: string; tickerLabel: string
  extraFields?: 'renda_fixa' | 'tesouro'
  brapiEnabled?: boolean; brapiSuggestType?: string
}

const TABS: AssetTab[] = [
  { key: 'acao',       label: 'Ação',       icon: <TrendingUp size={12} />, assetType: 'ACAO',              currency: 'BRL', tickerLabel: 'Ticker',       tickerPlaceholder: 'ex: PETR4 ou Petrobras',    brapiEnabled: true,  brapiSuggestType: 'stock'     },
  { key: 'fii',        label: 'FII',        icon: <Building2  size={12} />, assetType: 'FII',               currency: 'BRL', tickerLabel: 'Ticker',       tickerPlaceholder: 'ex: MXRF11 ou Maxi Renda',  brapiEnabled: true,  brapiSuggestType: 'fund'      },
  { key: 'etf_br',     label: 'ETF BR',     icon: <BarChart2  size={12} />, assetType: 'ETF_NACIONAL',      currency: 'BRL', tickerLabel: 'Ticker',       tickerPlaceholder: 'ex: BOVA11 ou IVVB11',      brapiEnabled: true,  brapiSuggestType: 'etf'       },
  { key: 'bdr',        label: 'BDR',        icon: <Globe2     size={12} />, assetType: 'BDR',               currency: 'BRL', tickerLabel: 'Ticker',       tickerPlaceholder: 'ex: NVDC34 ou AAPL34',      brapiEnabled: true,  brapiSuggestType: 'stock'     },
  { key: 'stock',      label: 'Stock',      icon: <Globe      size={12} />, assetType: 'STOCK',             currency: 'USD', tickerLabel: 'Ticker',       tickerPlaceholder: 'ex: AAPL ou Apple',         brapiEnabled: true,  brapiSuggestType: 'stock_int' },
  { key: 'etf_int',    label: 'ETF INT',    icon: <Globe      size={12} />, assetType: 'ETF_INTERNACIONAL', currency: 'USD', tickerLabel: 'Ticker',       tickerPlaceholder: 'ex: VTI ou Vanguard',       brapiEnabled: true,  brapiSuggestType: 'etf_int'   },
  { key: 'tesouro',    label: 'Tesouro',    icon: <Landmark   size={12} />, assetType: 'TESOURO_DIRETO',    currency: 'BRL', tickerLabel: 'Título',       tickerPlaceholder: 'ex: Tesouro IPCA 2029',     brapiEnabled: false, extraFields: 'tesouro'        },
  { key: 'renda_fixa', label: 'Renda Fixa', icon: <Banknote   size={12} />, assetType: 'RENDA_FIXA',        currency: 'BRL', tickerLabel: 'Código/Nome',  tickerPlaceholder: 'ex: CDB XP 110% CDI',       brapiEnabled: false, extraFields: 'renda_fixa'     },
  { key: 'cripto',     label: 'Cripto',     icon: <Bitcoin    size={12} />, assetType: 'CRIPTO',            currency: 'BRL', tickerLabel: 'Ticker',       tickerPlaceholder: 'ex: BTC ou Bitcoin',        brapiEnabled: true,  brapiSuggestType: 'cripto'    },
]

const RF_INDEXERS = ['CDI', 'IPCA', 'Prefixado', 'SELIC', 'IGP-M', 'Outro']
const TD_INDEXERS = ['IPCA+', 'Prefixado', 'SELIC']
const TODAY       = new Date().toISOString().split('T')[0]

const fieldStyle: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '0.3rem' }
const labelStyle: React.CSSProperties = {
  fontSize: 'var(--text-xs)', fontWeight: 500,
  color: 'var(--color-text-muted)', letterSpacing: '0.01em',
}
const inputStyle: React.CSSProperties = {
  width: '100%', padding: '0.5rem 0.75rem',
  borderRadius: 'var(--radius-md)',
  border: '1px solid oklch(from var(--color-text) l c h / 0.11)',
  background: 'var(--color-surface-2)',
  color: 'var(--color-text)',
  fontSize: 'var(--text-xs)',
  outline: 'none',
  transition: 'border-color 150ms ease, box-shadow 150ms ease',
  boxSizing: 'border-box',
}
const inputFocusStyle: React.CSSProperties = {
  borderColor: 'var(--color-primary)',
  boxShadow: '0 0 0 3px oklch(from var(--color-primary) l c h / 0.14)',
}

function Field({ label, required, badge, children, style }: {
  label: string; required?: boolean; badge?: React.ReactNode;
  children: React.ReactNode; style?: React.CSSProperties
}) {
  return (
    <div style={{ ...fieldStyle, ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 4 }}>
        <label style={labelStyle}>
          {label}{required && <span style={{ color: 'var(--color-notification)', marginLeft: 2 }}>*</span>}
        </label>
        {badge}
      </div>
      {children}
    </div>
  )
}

function Input(props: React.InputHTMLAttributes<HTMLInputElement> & { highlight?: boolean }) {
  const { highlight, style, onFocus, onBlur, ...rest } = props
  return (
    <input
      {...rest}
      style={{
        ...inputStyle,
        ...(highlight ? { borderColor: 'oklch(from var(--color-primary) l c h / 0.5)' } : {}),
        ...style,
      }}
      onFocus={e => { Object.assign(e.target.style, inputFocusStyle); onFocus?.(e) }}
      onBlur={e  => {
        e.target.style.borderColor = highlight ? 'oklch(from var(--color-primary) l c h / 0.5)' : 'oklch(from var(--color-text) l c h / 0.11)'
        e.target.style.boxShadow = 'none'
        onBlur?.(e)
      }}
    />
  )
}

function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  const { style, onFocus, onBlur, ...rest } = props
  return (
    <select
      {...rest}
      style={{ ...inputStyle, ...style }}
      onFocus={e => { Object.assign(e.target.style, inputFocusStyle); onFocus?.(e) }}
      onBlur={e  => {
        e.target.style.borderColor = 'oklch(from var(--color-text) l c h / 0.11)'
        e.target.style.boxShadow = 'none'
        onBlur?.(e)
      }}
    />
  )
}

// ── Extrai mensagem amigável do erro do backend ───────────────────────────────────
function extractErrorMessage(err: unknown): string {
  const e = err as {
    response?: { status?: number; data?: { detail?: unknown } }
    message?: string
  }
  const detail = e?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((d: any) => d?.msg ?? JSON.stringify(d)).join('; ')
  }
  if (e?.response?.status === 422)
    return 'Dados inválidos. Verifique o ticker, tipo de ativo e a data.'
  if (e?.response?.status === 400) return typeof detail === 'string' ? detail : 'Operação inválida.'
  if (e?.response?.status === 401) return 'Sessão expirada. Faça login novamente.'
  if (e?.response?.status === 404) return 'Carteira não encontrada.'
  if (e?.message) return e.message
  return 'Erro ao salvar lançamento. Tente novamente.'
}

export default function AddTransactionModal({ onClose }: Props) {
  const selectedPortfolioId                                = useAppStore(s => s.selectedPortfolioId)
  const prefill                                            = useAppStore(s => s.transactionModal.prefill)
  const { mutateAsync: createAsync, isPending: isCreating } = useCreateTransaction()
  const { mutateAsync: updateAsync, isPending: isUpdating } = useUpdateTransaction()
  const isPending  = isCreating || isUpdating
  const isEditMode = !!prefill?.transactionId
  const initialTab = prefill?.tab ?? 'acao'

  const [activeTab,     setActiveTab]     = useState(initialTab)
  const [operation,     setOperation]     = useState<'buy' | 'sell'>(prefill?.operation ?? 'buy')
  const [ticker,        setTicker]        = useState(prefill?.ticker    ?? '')
  const [assetName,     setAssetName]     = useState(prefill?.assetName ?? '')
  const [quantity,      setQuantity]      = useState(prefill?.quantity  != null ? String(prefill.quantity)  : '')
  const [price,         setPrice]         = useState(prefill?.price     != null ? String(prefill.price)     : '')
  const [fees,          setFees]          = useState(prefill?.fees      != null ? String(prefill.fees)      : '')
  const [date,          setDate]          = useState(prefill?.date      ?? TODAY)
  const [notes,         setNotes]         = useState(prefill?.notes     ?? '')
  const [currency,      setCurrency]      = useState(prefill?.currency  ?? TABS.find(t => t.key === initialTab)?.currency ?? 'BRL')
  const [error,         setError]         = useState<string | null>(null)
  const [success,       setSuccess]       = useState(false)
  const [priceFromBrapi, setPriceFromBrapi] = useState(false)
  const [indexer,       setIndexer]       = useState('')
  const [rate,          setRate]          = useState('')
  const [maturity,      setMaturity]      = useState('')
  const [issuer,        setIssuer]        = useState('')
  const [activeSlug,    setActiveSlug]    = useState('')
  const [priceEdited,   setPriceEdited]   = useState(isEditMode)
  const [showTDSugg,    setShowTDSugg]    = useState(false)
  const [showRVSugg,    setShowRVSugg]    = useState(false)
  const dropdownRef                        = useRef<HTMLDivElement>(null)

  const tab            = TABS.find(t => t.key === activeTab)!
  const isRF           = tab.extraFields === 'renda_fixa'
  const isTesouro      = tab.extraFields === 'tesouro'
  const indexerOptions = isTesouro ? TD_INDEXERS : RF_INDEXERS
  const modalTitle     = isEditMode ? `Editar — ${ticker}` : prefill?.ticker ? `Adicionar Cotas — ${prefill.ticker}` : 'Novo Lançamento'

  const { quote, loading: quoteLoading, error: quoteError } = useTickerQuote(ticker, !!tab.brapiEnabled && !isEditMode, date)
  const { items: tdItems, loading: tdLoading }               = useTesouroSearch(ticker, isTesouro && !isEditMode)
  const { items: rvItems, loading: rvLoading }               = useTickerSuggest(ticker, !!tab.brapiSuggestType && !isEditMode, tab.brapiSuggestType)
  const { price: tdPrice, loading: tdPriceLoading }          = useTreasuryPrice(activeSlug, date, isTesouro && !!activeSlug && !priceEdited)
  const anyLoading = quoteLoading || tdLoading || rvLoading || tdPriceLoading

  useEffect(() => {
    if (isEditMode || !quote) { setPriceFromBrapi(false); return }
    if (quote.price !== null && !price) { setPrice(String(quote.price)); setPriceFromBrapi(true) }
    if (quote.name && !assetName) setAssetName(quote.name)
    if (quote.currency) setCurrency(quote.currency.toUpperCase())
  }, [quote])

  const prevDate = useRef(date)
  useEffect(() => {
    if (isEditMode) return
    if (prevDate.current !== date && tab.brapiEnabled && ticker.length >= 2) {
      setPrice(''); setPriceFromBrapi(false); setPriceEdited(false)
    }
    prevDate.current = date
  }, [date])

  useEffect(() => {
    if (tdPrice !== null && tdPrice !== undefined && isTesouro && !priceEdited) {
      setPrice(String(tdPrice)); setPriceFromBrapi(true)
    }
  }, [tdPrice, isTesouro, priceEdited])

  useEffect(() => {
    if (isTesouro && activeSlug && !priceEdited) { setPrice(''); setPriceFromBrapi(false) }
  }, [date, isTesouro, activeSlug])

  useEffect(() => {
    if (isTesouro && tdItems.length > 0) setShowTDSugg(true); else setShowTDSugg(false)
  }, [tdItems, isTesouro])

  useEffect(() => {
    if (tab.brapiSuggestType && rvItems.length > 0) setShowRVSugg(true); else setShowRVSugg(false)
  }, [rvItems, tab.brapiSuggestType])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowTDSugg(false); setShowRVSugg(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function applyTDSuggestion(item: TreasuryItem) {
    setTicker(item.name); setAssetName(item.name)
    setActiveSlug((item as any).slug || item.ticker)
    if (item.indexer) setIndexer(item.indexer)
    if (item.rate != null) setRate(String(item.rate))
    if (item.maturity_date) setMaturity(item.maturity_date.slice(0, 10))
    setPrice(''); setPriceFromBrapi(false); setPriceEdited(false); setShowTDSugg(false)
  }

  function applyRVSuggestion(item: TickerSuggestion) {
    setTicker(item.ticker); setAssetName(item.name)
    setPrice(''); setPriceFromBrapi(false); setPriceEdited(false); setShowRVSugg(false)
  }

  function handleTabChange(key: string) {
    const t = TABS.find(t => t.key === key)!
    setActiveTab(key); setCurrency(t.currency)
    if (!prefill?.ticker) { setTicker(''); setAssetName('') }
    setPrice(''); setIndexer(''); setRate(''); setMaturity(''); setIssuer('')
    setActiveSlug(''); setPriceEdited(false); setPriceFromBrapi(false)
    setShowTDSugg(false); setShowRVSugg(false); setError(null)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(null)

    if (!selectedPortfolioId) {
      setError('Selecione uma carteira antes de lançar.')
      return
    }

    const qty = parseFloat(quantity)
    const prc = parseFloat(price)
    const fee = parseFloat(fees || '0')

    if (!ticker.trim())          { setError('Informe o ticker/código do ativo.'); return }
    if (isNaN(qty) || qty <= 0)  { setError('Quantidade deve ser maior que zero.'); return }
    if (isNaN(prc) || prc <= 0)  { setError('Preço deve ser maior que zero.'); return }
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

    const finalTicker = isTesouro && activeSlug ? activeSlug : ticker.trim().toUpperCase()
    const payload = {
      ticker:     finalTicker,
      asset_type: tab.assetType,
      operation,
      quantity:   qty,
      price:      prc,
      fees:       isNaN(fee) ? 0 : fee,
      date,
      currency,
      notes:      enrichedNotes || undefined,
    }

    try {
      if (isEditMode && prefill?.transactionId) {
        await updateAsync({ portfolioId: selectedPortfolioId, id: prefill.transactionId, data: payload })
      } else {
        await createAsync({ portfolioId: selectedPortfolioId, data: payload })
      }
      setSuccess(true)
    } catch (err: unknown) {
      setError(extractErrorMessage(err))
    }
  }

  function handleReset() {
    setSuccess(false)
    setTicker(prefill?.ticker ?? ''); setAssetName(prefill?.assetName ?? '')
    setQuantity(''); setPrice(''); setFees(''); setDate(TODAY); setNotes('')
    setIndexer(''); setRate(''); setMaturity(''); setIssuer('')
    setActiveSlug(''); setPriceEdited(false); setPriceFromBrapi(false)
    setShowTDSugg(false); setShowRVSugg(false); setError(null)
  }

  const total = quantity && price
    ? (parseFloat(quantity) * parseFloat(price) + parseFloat(fees || '0'))
        .toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : null

  const showDropdown  = showTDSugg || showRVSugg
  const dropdownItems = showTDSugg
    ? tdItems.map(item => ({
        label:    item.name,
        sublabel: `${item.indexer}${item.rate ? ` ${item.rate}% a.a.` : ''}${item.maturity_date ? ` • venc. ${item.maturity_date.slice(0, 7)}` : ''}`,
        onSelect: () => applyTDSuggestion(item),
      }))
    : rvItems.map(item => ({
        label: item.ticker, sublabel: item.name,
        onSelect: () => applyRVSuggestion(item),
      }))

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '1rem',
    }}>
      <div
        style={{ position: 'absolute', inset: 0, background: 'oklch(0.1 0.01 240 / 0.65)', backdropFilter: 'blur(6px)' }}
        onClick={onClose} aria-hidden
      />

      <div style={{
        position: 'relative', zIndex: 10,
        width: '100%', maxWidth: 500,
        background: 'var(--color-surface)',
        border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
        borderRadius: 'var(--radius-xl)',
        boxShadow: 'var(--shadow-lg)',
        overflow: 'hidden',
        display: 'flex', flexDirection: 'column',
        maxHeight: '92dvh',
      }}>

        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '1rem 1.25rem',
          borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 650, color: 'var(--color-text)', letterSpacing: '-0.01em' }}>
            {modalTitle}
          </span>
          <button
            onClick={onClose}
            style={{
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              width: 28, height: 28, borderRadius: 'var(--radius-md)',
              border: 'none', background: 'transparent',
              color: 'var(--color-text-muted)', cursor: 'pointer',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.07)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            aria-label="Fechar"
          >
            <X size={15} />
          </button>
        </div>

        {/* Success */}
        {success ? (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', gap: '1rem',
            padding: '3rem 1.5rem', textAlign: 'center',
          }}>
            <div style={{
              width: 52, height: 52, borderRadius: '50%',
              background: 'oklch(from var(--color-success) l c h / 0.12)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <CheckCircle2 size={26} style={{ color: 'var(--color-success)' }} />
            </div>
            <div>
              <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
                {isEditMode ? 'Lançamento atualizado!' : 'Lançamento registrado!'}
              </p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 4 }}>
                {isEditMode ? 'As alterações foram salvas com sucesso.' : 'O lançamento foi adicionado à sua carteira.'}
              </p>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
              {!isEditMode && (
                <button onClick={handleReset} className="btn btn-secondary" style={{ fontSize: 'var(--text-xs)', padding: '0.4375rem 1rem' }}>
                  Novo lançamento
                </button>
              )}
              <button onClick={onClose} className="btn btn-primary" style={{ fontSize: 'var(--text-xs)', padding: '0.4375rem 1rem' }}>
                Fechar
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>

            {/* Abas — flexWrap para não perder Renda Fixa/Cripto fora do viewport */}
            <div style={{
              display: 'flex', gap: 4, rowGap: 4,
              flexWrap: 'wrap',
              padding: '0.875rem 1.25rem 0',
              flexShrink: 0,
            }}>
              {TABS.map(t => {
                const isActive = activeTab === t.key
                return (
                  <button
                    key={t.key} type="button"
                    onClick={() => !isEditMode && handleTabChange(t.key)}
                    style={{
                      flexShrink: 0,
                      display: 'flex', alignItems: 'center', gap: 5,
                      padding: '5px 10px',
                      borderRadius: 'var(--radius-lg)',
                      border: isActive
                        ? '1px solid oklch(from var(--color-primary) l c h / 0.3)'
                        : '1px solid transparent',
                      background: isActive
                        ? 'oklch(from var(--color-primary) l c h / 0.12)'
                        : 'transparent',
                      color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
                      fontSize: 'var(--text-xs)', fontWeight: isActive ? 600 : 400,
                      cursor: isEditMode && !isActive ? 'default' : 'pointer',
                      opacity: isEditMode && !isActive ? 0.35 : 1,
                      transition: 'all 150ms ease', whiteSpace: 'nowrap',
                    }}
                  >
                    {t.icon}{t.label}
                  </button>
                )
              })}
            </div>

            <div style={{ height: 1, background: 'oklch(from var(--color-text) l c h / 0.07)', margin: '0.625rem 1.25rem 0', flexShrink: 0 }} />

            {/* Campos */}
            <div style={{
              flex: 1, overflowY: 'auto', overflowX: 'hidden',
              padding: '1rem 1.25rem',
              display: 'flex', flexDirection: 'column', gap: '0.875rem',
            }}>

              {/* Toggle Compra/Venda */}
              <div style={{
                display: 'grid', gridTemplateColumns: '1fr 1fr',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
                overflow: 'hidden', background: 'var(--color-surface-2)',
              }}>
                {(['buy', 'sell'] as const).map(op => {
                  const isSel = operation === op
                  const isBuy = op === 'buy'
                  const color = isBuy ? 'var(--color-success)' : 'var(--color-notification)'
                  return (
                    <button key={op} type="button" onClick={() => setOperation(op)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                        padding: '0.5625rem', border: 'none',
                        background: isSel ? `oklch(from ${color} l c h / 0.14)` : 'transparent',
                        color: isSel ? color : 'var(--color-text-muted)',
                        fontSize: 'var(--text-xs)', fontWeight: isSel ? 600 : 400,
                        cursor: 'pointer', transition: 'all 150ms ease',
                      }}
                    >
                      {isBuy
                        ? <ArrowDownCircle size={13} style={{ flexShrink: 0 }} />
                        : <ArrowUpCircle   size={13} style={{ flexShrink: 0 }} />}
                      {isBuy ? 'Compra' : 'Venda'}
                    </button>
                  )
                })}
              </div>

              {/* Ticker + Moeda */}
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <Field label={tab.tickerLabel} style={{ flex: 1 }}>
                  <div ref={dropdownRef} style={{ position: 'relative' }}>
                    <Input
                      type="text" value={ticker}
                      onChange={e => {
                        if (isEditMode) return
                        const v = e.target.value
                        setTicker(v)
                        if (!prefill?.ticker) setAssetName('')
                        setPrice(''); setPriceFromBrapi(false); setPriceEdited(false)
                        if (isTesouro) setActiveSlug('')
                      }}
                      onFocus={() => {
                        if (!isEditMode) {
                          if (isTesouro && tdItems.length > 0) setShowTDSugg(true)
                          if (tab.brapiSuggestType && rvItems.length > 0) setShowRVSugg(true)
                        }
                      }}
                      placeholder={tab.tickerPlaceholder}
                      style={{ paddingRight: anyLoading ? '2.25rem' : '0.75rem', opacity: isEditMode ? 0.65 : 1 }}
                      readOnly={isEditMode}
                      autoFocus={!isEditMode}
                    />
                    {anyLoading && (
                      <span style={{ position: 'absolute', right: '0.625rem', top: '50%', transform: 'translateY(-50%)' }}>
                        <Loader2 size={13} style={{ color: 'var(--color-primary)', animation: 'spin 1s linear infinite' }} />
                      </span>
                    )}
                    {showDropdown && dropdownItems.length > 0 && (
                      <div style={{
                        position: 'absolute', top: 'calc(100% + 4px)', left: 0, right: 0, zIndex: 60,
                        background: 'var(--color-surface-2)',
                        border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
                        borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)',
                        overflow: 'hidden', maxHeight: 200, overflowY: 'auto',
                      }}>
                        {dropdownItems.map((item, i) => (
                          <button key={i} type="button" onMouseDown={item.onSelect}
                            style={{
                              width: '100%', textAlign: 'left',
                              padding: '0.5rem 0.75rem',
                              background: 'transparent', border: 'none',
                              borderBottom: i < dropdownItems.length - 1 ? '1px solid oklch(from var(--color-text) l c h / 0.06)' : 'none',
                              cursor: 'pointer',
                            }}
                            onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.07)')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                          >
                            <span style={{ display: 'block', fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)' }}>{item.label}</span>
                            {item.sublabel && <span style={{ display: 'block', fontSize: '0.68rem', color: 'var(--color-text-muted)', marginTop: 1 }}>{item.sublabel}</span>}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  {assetName  && <p style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', margin: 0 }}>{assetName}</p>}
                  {quoteError && !quoteLoading && <p style={{ fontSize: '0.68rem', color: 'var(--color-text-muted)', margin: 0 }}>{quoteError}</p>}
                </Field>

                <Field label="Moeda" style={{ width: 86 }}>
                  <Select value={currency} onChange={e => setCurrency(e.target.value)}>
                    <option value="BRL">BRL</option>
                    <option value="USD">USD</option>
                    <option value="EUR">EUR</option>
                    <option value="BTC">BTC</option>
                  </Select>
                </Field>
              </div>

              {/* Campos RF / Tesouro */}
              {(isRF || isTesouro) && (
                <div style={{
                  borderRadius: 'var(--radius-lg)',
                  border: '1px solid oklch(from var(--color-primary) l c h / 0.15)',
                  background: 'oklch(from var(--color-primary) l c h / 0.04)',
                  padding: '0.875rem',
                  display: 'flex', flexDirection: 'column', gap: '0.75rem',
                }}>
                  <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-primary)', margin: 0 }}>
                    {isTesouro ? 'Dados do Título' : 'Dados do Ativo'}
                  </p>
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <Field label="Indexador" required style={{ flex: 1 }}>
                      <Select value={indexer} onChange={e => setIndexer(e.target.value)}>
                        <option value="">Selecionar…</option>
                        {indexerOptions.map(o => <option key={o} value={o}>{o}</option>)}
                      </Select>
                    </Field>
                    <Field label="Taxa (% a.a.)" style={{ width: 100 }}>
                      <Input type="number" value={rate} onChange={e => setRate(e.target.value)}
                        placeholder={isTesouro ? 'ex: 5.82' : 'ex: 110'} min="0" step="any" />
                    </Field>
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <Field label="Vencimento" style={{ flex: 1 }}>
                      <Input type="date" value={maturity} onChange={e => setMaturity(e.target.value)} />
                    </Field>
                    {isRF && (
                      <Field label="Emissor" style={{ flex: 1 }}>
                        <Input type="text" value={issuer} onChange={e => setIssuer(e.target.value)} placeholder="ex: Banco XP" />
                      </Field>
                    )}
                  </div>
                </div>
              )}

              {/* Quantidade + Preço */}
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <Field label={isRF || isTesouro ? 'Qtd / Cotas' : 'Quantidade'} style={{ flex: 1 }}>
                  <Input type="number" value={quantity} onChange={e => setQuantity(e.target.value)}
                    placeholder="0" min="0" step="any" />
                </Field>
                <Field
                  label={`${isRF || isTesouro ? 'PU / Preço unit.' : 'Preço'} (${currency})`}
                  style={{ flex: 1 }}
                  badge={priceFromBrapi && (
                    <span style={{
                      display: 'flex', alignItems: 'center', gap: 3,
                      fontSize: '0.65rem', fontWeight: 600,
                      color: 'var(--color-primary)',
                      background: 'oklch(from var(--color-primary) l c h / 0.1)',
                      border: '1px solid oklch(from var(--color-primary) l c h / 0.2)',
                      borderRadius: 'var(--radius-full)', padding: '1px 6px',
                    }}>
                      <Zap size={8} /> BRAPI
                    </span>
                  )}
                >
                  <Input
                    type="number" value={price}
                    onChange={e => { setPrice(e.target.value); setPriceFromBrapi(false); setPriceEdited(true) }}
                    placeholder="0,00" min="0" step="any"
                    highlight={priceFromBrapi}
                  />
                </Field>
              </div>

              {/* Taxas + Data */}
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <Field label="Taxas / Corretagem" style={{ flex: 1 }}>
                  <Input type="number" value={fees} onChange={e => setFees(e.target.value)}
                    placeholder="0,00" min="0" step="any" />
                </Field>
                <Field label="Data da operação" style={{ flex: 1 }}>
                  <Input type="date" value={date} onChange={e => setDate(e.target.value)} />
                </Field>
              </div>

              {/* Total estimado */}
              {total && (
                <div style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '0.625rem 0.875rem',
                  borderRadius: 'var(--radius-lg)',
                  background: 'oklch(from var(--color-primary) l c h / 0.07)',
                  border: '1px solid oklch(from var(--color-primary) l c h / 0.15)',
                }}>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Total estimado</span>
                  <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--color-text)', fontVariantNumeric: 'tabular-nums' }}>
                    {currency} {total}
                  </span>
                </div>
              )}

              {/* Observações */}
              <Field label="Observações" badge={<span style={{ fontSize: '0.68rem', color: 'var(--color-text-faint)' }}>opcional</span>}>
                <textarea
                  value={notes} onChange={e => setNotes(e.target.value)}
                  rows={2} placeholder="Anotações sobre o lançamento…"
                  style={{ ...inputStyle, resize: 'none', lineHeight: 1.5 }}
                  onFocus={e => Object.assign(e.target.style, inputFocusStyle)}
                  onBlur={e  => { e.target.style.borderColor = 'oklch(from var(--color-text) l c h / 0.11)'; e.target.style.boxShadow = 'none' }}
                />
              </Field>

              {/* Erro */}
              {error && (
                <div style={{
                  fontSize: 'var(--text-xs)', color: 'var(--color-notification)',
                  background: 'oklch(from var(--color-notification) l c h / 0.08)',
                  border: '1px solid oklch(from var(--color-notification) l c h / 0.2)',
                  borderRadius: 'var(--radius-md)', padding: '0.5rem 0.75rem',
                }}>
                  {error}
                </div>
              )}
            </div>

            {/* Footer */}
            <div style={{
              display: 'flex', justifyContent: 'flex-end', gap: '0.5rem',
              padding: '0.875rem 1.25rem',
              borderTop: '1px solid oklch(from var(--color-text) l c h / 0.07)',
              flexShrink: 0,
            }}>
              <button type="button" onClick={onClose} className="btn btn-secondary"
                style={{ fontSize: 'var(--text-xs)', padding: '0.4375rem 1rem' }}>
                Cancelar
              </button>
              <button type="submit" disabled={isPending} className="btn btn-primary"
                style={{ fontSize: 'var(--text-xs)', padding: '0.4375rem 1.125rem', fontWeight: 650 }}>
                {isPending ? 'Salvando…' : isEditMode ? 'Salvar Alterações' : 'Salvar Lançamento'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
