import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { RefreshCw } from 'lucide-react'
import { useCreateTransaction } from '@/hooks/useTransactions'
import { useUsdBrl } from '@/hooks/useFxRate'
import { formatBRL, formatUSD } from '@/utils/format'
import type { TransactionCreate } from '@/hooks/useTransactions'

// ── Configuração por tipo de ativo ────────────────────────────────────
type AssetConfig = {
  label: string
  currency: 'BRL' | 'USD'
  qtyStep: string
  qtyDefault: string
  isRendaFixa?: boolean
}

const ASSET_CONFIGS: Record<string, AssetConfig> = {
  ACAO_NACIONAL:     { label: 'Ações',              currency: 'BRL', qtyStep: '1',          qtyDefault: '1' },
  FII:               { label: 'FIIs',               currency: 'BRL', qtyStep: '1',          qtyDefault: '1' },
  ETF_NACIONAL:      { label: 'ETFs Nacionais',      currency: 'BRL', qtyStep: '1',          qtyDefault: '1' },
  BDR:               { label: 'BDRs',                currency: 'BRL', qtyStep: '1',          qtyDefault: '1' },
  TESOURO_DIRETO:    { label: 'Tesouro Direto',      currency: 'BRL', qtyStep: '0.01',       qtyDefault: '0.01' },
  STOCK:             { label: 'Stock',               currency: 'USD', qtyStep: '0.00000001', qtyDefault: '0.00000001' },
  ETF_INTERNACIONAL: { label: 'ETFs Internacionais', currency: 'USD', qtyStep: '0.00000001', qtyDefault: '0.00000001' },
  REIT:              { label: 'Reit',                currency: 'USD', qtyStep: '0.00000001', qtyDefault: '0.00000001' },
  CRIPTO:            { label: 'Criptomoedas',        currency: 'BRL', qtyStep: '0.00000001', qtyDefault: '0.00000001' },
  RENDA_FIXA:        { label: 'Renda Fixa',          currency: 'BRL', qtyStep: '0.01',       qtyDefault: '0.01', isRendaFixa: true },
}

const BOND_TYPES = ['CDB','LCI','LCA','LC','LIG','CRI','CRA','Debenture','PGBL','VGBL','Outro']
const INDEXERS   = ['CDI','IPCA','IGP-M','Prefixado','SELIC','Outro']
const BOND_FORMS = ['Pós-fixado','Prefixado','Híbrido']

const TX_TYPES = [
  { value: 'COMPRA',        label: 'Compra' },
  { value: 'VENDA',         label: 'Venda' },
  { value: 'BONIFICACAO',   label: 'Bonificação' },
  { value: 'DESDOBRAMENTO', label: 'Desdobramento' },
  { value: 'GRUPAMENTO',    label: 'Grupamento' },
] as const

const labelStyle = { color: 'var(--color-text-muted)', fontSize: 12, fontWeight: 500, marginBottom: 4, display: 'block' }
const errStyle   = { color: 'var(--color-error)', fontSize: 11, marginTop: 2 }
const inputStyle = { fontSize: 16 }

interface FormValues extends TransactionCreate {
  fx_rate_input: string
  issuer?: string
  bond_type?: string
  indexer?: string
  cdi_rate?: number
  bond_form?: string
  maturity_date?: string
  daily_liquidity?: boolean
}

interface Props { portfolioId: number; onClose: () => void }

export default function TransactionForm({ portfolioId, onClose }: Props) {
  const { data: fxData, isLoading: loadingFx } = useUsdBrl()
  const { mutate: createTx, isPending } = useCreateTransaction()

  const { register, handleSubmit, watch, setValue, control, formState: { errors } } = useForm<FormValues>({
    defaultValues: {
      transaction_type: 'COMPRA',
      asset_type: 'ACAO_NACIONAL',
      transaction_date: new Date().toISOString().slice(0, 10),
      fees: 0, daily_liquidity: false, fx_rate_input: '',
    },
  })

  const assetType   = watch('asset_type')
  const txType      = watch('transaction_type')
  const qty         = Number(watch('quantity')) || 0
  const price       = Number(watch('price'))    || 0
  const fees        = Number(watch('fees'))     || 0
  const fxRateInput = watch('fx_rate_input')
  const fxRate      = parseFloat(fxRateInput) || fxData?.rate || 0

  const cfg         = ASSET_CONFIGS[assetType] ?? ASSET_CONFIGS.ACAO_NACIONAL
  const isUSD       = cfg.currency === 'USD'
  const isRendaFixa = !!cfg.isRendaFixa

  useEffect(() => {
    if (fxData?.rate && !fxRateInput) setValue('fx_rate_input', String(fxData.rate.toFixed(4)))
  }, [fxData, fxRateInput, setValue])

  useEffect(() => {
    setValue('quantity', parseFloat(cfg.qtyDefault))
    setValue('price', 0)
  }, [assetType, cfg.qtyDefault, setValue])

  const priceBrl  = isUSD ? price * fxRate : price
  const totalBrl  = qty * priceBrl + fees
  const totalOrig = qty * price + fees

  function onSubmit(data: FormValues) {
    // Separa campos auxiliares de UI do payload real
    const payload: TransactionCreate & { fx_rate?: number } = {
      ticker:           data.ticker,
      asset_type:       data.asset_type,
      operation:        data.operation,
      quantity:         data.quantity,
      price:            data.price,
      fees:             data.fees,
      date:             data.date,
      notes:            data.notes,
      currency:         cfg.currency,
      ...(isUSD && { fx_rate: parseFloat(data.fx_rate_input) }),
    }
    createTx(
      { portfolioId, data: payload },
      { onSuccess: onClose },
    )
  }

  const buyActive  = txType === 'COMPRA'
  const sellActive = txType === 'VENDA'

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 p-1">

      <div
        className="flex rounded-lg overflow-hidden border"
        style={{ borderColor: 'var(--color-border)' }}
      >
        {TX_TYPES.slice(0, 2).map(t => (
          <button
            key={t.value} type="button"
            onClick={() => setValue('transaction_type', t.value)}
            className="flex-1 py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-1.5"
            style={{
              background: txType === t.value
                ? t.value === 'COMPRA'
                  ? 'oklch(from var(--color-success) l c h / 0.15)'
                  : 'oklch(from var(--color-notification) l c h / 0.15)'
                : 'transparent',
              color: txType === t.value
                ? t.value === 'COMPRA' ? 'var(--color-success)' : 'var(--color-notification)'
                : 'var(--color-text-muted)',
              minHeight: 44,
            }}
          >
            {t.value === 'COMPRA' ? '🟢' : '🔴'} {t.label}
          </button>
        ))}
      </div>

      <div className="flex gap-2 flex-wrap">
        {TX_TYPES.slice(2).map(t => (
          <button
            key={t.value} type="button"
            onClick={() => setValue('transaction_type', t.value)}
            className="px-3 py-1 rounded text-xs font-medium border transition-colors"
            style={{
              background: txType === t.value ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent',
              color: txType === t.value ? 'var(--color-primary)' : 'var(--color-text-muted)',
              borderColor: txType === t.value ? 'var(--color-primary)' : 'var(--color-border)',
              minHeight: 36,
            }}
          >{t.label}</button>
        ))}
      </div>

      <div>
        <label style={labelStyle}>Tipo de ativo</label>
        <select className="input mt-1" style={inputStyle} {...register('asset_type')}>
          {Object.entries(ASSET_CONFIGS).map(([v, c]) => (
            <option key={v} value={v}>{c.label}</option>
          ))}
        </select>
      </div>

      {isRendaFixa && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label style={labelStyle}>Emissor</label>
              <input className="input mt-1" style={inputStyle} placeholder="Ex: Banco XP" {...register('issuer')} />
            </div>
            <div>
              <label style={labelStyle}>Tipo de título</label>
              <select className="input mt-1" style={inputStyle} {...register('bond_type')}>
                {BOND_TYPES.map(b => <option key={b}>{b}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label style={labelStyle}>Indexador</label>
              <select className="input mt-1" style={inputStyle} {...register('indexer')}>
                {INDEXERS.map(i => <option key={i}>{i}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Taxa do CDI (%)</label>
              <input type="number" step="0.01" className="input mt-1" style={inputStyle}
                placeholder="100" {...register('cdi_rate', { valueAsNumber: true })} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label style={labelStyle}>Forma <span style={{ color: 'var(--color-text-faint)' }}>(Opcional)</span></label>
              <select className="input mt-1" style={inputStyle} {...register('bond_form')}>
                {BOND_FORMS.map(f => <option key={f}>{f}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Valor (Opcional)</label>
              <input type="number" step="0.01" className="input mt-1" style={inputStyle} placeholder="0,00"
                {...register('price', { valueAsNumber: true })} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 items-center">
            <div>
              <label style={labelStyle}>Data da transação</label>
              <input type="date" className="input mt-1" style={inputStyle} {...register('transaction_date')} />
            </div>
            <div>
              <label style={labelStyle}>Data de vencimento</label>
              <input type="date" className="input mt-1" style={inputStyle} {...register('maturity_date')} />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label style={{ ...labelStyle, marginBottom: 0 }}>Liquidez diária</label>
            <Controller
              control={control} name="daily_liquidity"
              render={({ field }) => (
                <button
                  type="button" role="switch" aria-checked={field.value}
                  onClick={() => field.onChange(!field.value)}
                  className="relative inline-flex h-5 w-9 rounded-full transition-colors"
                  style={{
                    background: field.value ? 'var(--color-success)' : 'var(--color-divider)',
                  }}
                >
                  <span
                    className="inline-block h-4 w-4 rounded-full bg-white shadow transition-transform mt-0.5"
                    style={{ transform: field.value ? 'translateX(1rem)' : 'translateX(2px)' }}
                  />
                </button>
              )}
            />
          </div>
        </>
      )}

      {!isRendaFixa && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label style={labelStyle}>Ativo</label>
              <input
                className="input mt-1 uppercase placeholder:normal-case"
                style={inputStyle}
                placeholder="Selecionar"
                {...register('ticker', { required: 'Obrigatório' })}
                onChange={e => setValue('ticker', e.target.value.toUpperCase())}
              />
              {errors.ticker && <p style={errStyle}>{errors.ticker.message}</p>}
            </div>
            <div>
              <label style={labelStyle}>Data da transação</label>
              <input type="date" className="input mt-1" style={inputStyle} {...register('transaction_date', { required: true })} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label style={labelStyle}>Quantidade</label>
              <input
                type="number" step={cfg.qtyStep} min={cfg.qtyStep}
                className="input mt-1" style={inputStyle}
                inputMode="decimal"
                {...register('quantity', { required: true, valueAsNumber: true })}
              />
              {errors.quantity && <p style={errStyle}>Obrigatório</p>}
            </div>
            <div>
              <label style={labelStyle}>Preço em {isUSD ? 'US$' : 'R$'}</label>
              <input
                type="number" step={isUSD ? '0.00000001' : '0.01'} min="0"
                className="input mt-1" style={inputStyle}
                placeholder="0,00" inputMode="decimal"
                {...register('price', { required: true, valueAsNumber: true })}
              />
              {errors.price && <p style={errStyle}>Obrigatório</p>}
            </div>
          </div>

          {isUSD && (
            <div
              className="rounded-lg p-3"
              style={{
                background: 'oklch(from var(--color-primary) l c h / 0.07)',
                border:     '1px solid oklch(from var(--color-primary) l c h / 0.2)',
              }}
            >
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium" style={{ color: 'var(--color-primary)' }}>Cotação USD/BRL</label>
                {loadingFx && <RefreshCw size={12} className="animate-spin" style={{ color: 'var(--color-text-muted)' }} />}
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>US$ 1,00 =</span>
                <input
                  type="number" step="0.0001" min="0.01"
                  className="input py-1 text-xs w-28" style={inputStyle}
                  inputMode="decimal"
                  {...register('fx_rate_input', { required: isUSD })}
                />
                <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>R$</span>
                {fxData?.rate && (
                  <button
                    type="button"
                    onClick={() => setValue('fx_rate_input', String(fxData.rate.toFixed(4)))}
                    className="text-xs ml-auto"
                    style={{ color: 'var(--color-primary)' }}
                  >
                    Usar atual ({fxData.rate.toFixed(4)})
                  </button>
                )}
              </div>
              {price > 0 && fxRate > 0 && (
                <p className="text-xs mt-2" style={{ color: 'var(--color-text-muted)' }}>
                  {formatUSD(price)} × {fxRate.toFixed(4)} ={' '}
                  <span className="font-medium" style={{ color: 'var(--color-text)' }}>{formatBRL(priceBrl)}</span> por unidade
                </p>
              )}
            </div>
          )}

          <div>
            <label style={labelStyle}>Outros custos (R$) <span style={{ color: 'var(--color-text-faint)' }}>(Opcional)</span></label>
            <input
              type="number" step="0.01" min="0"
              className="input mt-1" style={inputStyle}
              placeholder="0,00" inputMode="decimal"
              {...register('fees', { valueAsNumber: true })}
            />
          </div>
        </>
      )}

      <div
        className="flex items-center justify-between px-4 py-3 rounded-lg"
        style={{ background: 'var(--color-surface-offset)' }}
      >
        <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>Valor total</span>
        <span
          className="text-base font-bold tabular-nums"
          style={{ color: sellActive ? 'var(--color-success)' : 'var(--color-text)' }}
        >
          {isUSD
            ? `${formatUSD(totalOrig)} = ${formatBRL(totalBrl)}`
            : formatBRL(totalBrl)}
        </span>
      </div>

      <div className="flex gap-2 pb-safe">
        <button
          type="button"
          onClick={onClose}
          className="flex-1 md:flex-none btn btn-secondary"
          style={{ minHeight: 44 }}
        >
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isPending}
          className="flex-1 md:flex-none btn btn-primary"
          style={{
            minHeight: 44,
            background: buyActive
              ? 'var(--color-success)'
              : sellActive
                ? 'var(--color-notification)'
                : 'var(--color-primary)',
            color: '#fff',
          }}
        >
          {isPending ? 'Salvando…' : '+ Adicionar Lançamento'}
        </button>
      </div>
    </form>
  )
}
