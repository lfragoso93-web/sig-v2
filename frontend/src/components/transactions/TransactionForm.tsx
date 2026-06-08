import { useState, useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import clsx from 'clsx'
import { RefreshCw } from 'lucide-react'
import { TransactionCreate } from '@/services/transactionService'
import { useCreateTransaction } from '@/hooks/useTransactions'
import { useUsdBrl } from '@/hooks/useFxRate'
import { formatBRL, formatUSD } from '@/utils/format'

// ─── Configuracao por tipo de ativo ──────────────────────────────────────────

type AssetConfig = {
  label: string
  currency: 'BRL' | 'USD'
  qtyStep: string
  qtyDefault: string
  isRendaFixa?: boolean
}

const ASSET_CONFIGS: Record<string, AssetConfig> = {
  ACAO_NACIONAL:      { label: 'Ações',                    currency: 'BRL', qtyStep: '1',          qtyDefault: '1' },
  FII:                { label: 'FIIs',                     currency: 'BRL', qtyStep: '1',          qtyDefault: '1' },
  ETF_NACIONAL:       { label: 'ETFs Nacionais',           currency: 'BRL', qtyStep: '1',          qtyDefault: '1' },
  BDR:                { label: 'BDRs',                     currency: 'BRL', qtyStep: '1',          qtyDefault: '1' },
  TESOURO_DIRETO:     { label: 'Tesouro Direto',           currency: 'BRL', qtyStep: '0.01',       qtyDefault: '0.01' },
  STOCK:              { label: 'Stock',                    currency: 'USD', qtyStep: '0.00000001', qtyDefault: '0.00000001' },
  ETF_INTERNACIONAL:  { label: 'ETFs Internacionais',      currency: 'USD', qtyStep: '0.00000001', qtyDefault: '0.00000001' },
  REIT:               { label: 'Reit',                     currency: 'USD', qtyStep: '0.00000001', qtyDefault: '0.00000001' },
  CRIPTO:             { label: 'Criptomoedas',             currency: 'BRL', qtyStep: '0.00000001', qtyDefault: '0.00000001' },
  RENDA_FIXA:         { label: 'Renda Fixa',               currency: 'BRL', qtyStep: '0.01',       qtyDefault: '0.01', isRendaFixa: true },
}

const BOND_TYPES = ['CDB', 'LCI', 'LCA', 'LC', 'LIG', 'CRI', 'CRA', 'Debenture', 'PGBL', 'VGBL', 'Outro']
const INDEXERS  = ['CDI', 'IPCA', 'IGP-M', 'Prefixado', 'SELIC', 'Outro']
const BOND_FORMS = ['Pós-fixado', 'Prefixado', 'Híbrido']

const TX_TYPES = [
  { value: 'COMPRA',       label: 'Compra' },
  { value: 'VENDA',        label: 'Venda' },
  { value: 'BONIFICACAO',  label: 'Bonificação' },
  { value: 'DESDOBRAMENTO',label: 'Desdobramento' },
  { value: 'GRUPAMENTO',   label: 'Grupamento' },
] as const

// ─── Props ────────────────────────────────────────────────────────────────────

interface FormValues extends TransactionCreate {
  fx_rate_input: string   // campo editavel da cotacao
  issuer?: string
  bond_type?: string
  indexer?: string
  cdi_rate?: number
  bond_form?: string
  maturity_date?: string
  daily_liquidity?: boolean
}

interface Props {
  portfolioId: number
  onClose: () => void
}

// ─── Componente ───────────────────────────────────────────────────────────────

export default function TransactionForm({ portfolioId, onClose }: Props) {
  const { data: fxData, isLoading: loadingFx } = useUsdBrl()
  const { mutate: createTx, isPending } = useCreateTransaction(portfolioId)

  const { register, handleSubmit, watch, setValue, control, formState: { errors } } = useForm<FormValues>({
    defaultValues: {
      transaction_type: 'COMPRA',
      asset_type: 'ACAO_NACIONAL',
      transaction_date: new Date().toISOString().slice(0, 10),
      fees: 0,
      daily_liquidity: false,
      fx_rate_input: '',
    },
  })

  const assetType    = watch('asset_type')
  const txType       = watch('transaction_type')
  const qty          = Number(watch('quantity'))  || 0
  const price        = Number(watch('price'))     || 0
  const fees         = Number(watch('fees'))      || 0
  const fxRateInput  = watch('fx_rate_input')
  const fxRate       = parseFloat(fxRateInput)   || fxData?.rate || 0

  const cfg = ASSET_CONFIGS[assetType] ?? ASSET_CONFIGS.ACAO_NACIONAL
  const isUSD = cfg.currency === 'USD'
  const isRendaFixa = !!cfg.isRendaFixa

  // Preenche cotacao automaticamente quando carrega
  useEffect(() => {
    if (fxData?.rate && !fxRateInput) {
      setValue('fx_rate_input', String(fxData.rate.toFixed(4)))
    }
  }, [fxData])

  // Recalcula campos ao trocar tipo de ativo
  useEffect(() => {
    setValue('currency', cfg.currency)
    setValue('quantity', parseFloat(cfg.qtyDefault))
    setValue('price', 0)
  }, [assetType])

  const priceBrl   = isUSD ? price * fxRate : price
  const totalBrl   = qty * priceBrl + fees
  const totalOrig  = qty * price + fees

  function onSubmit(data: FormValues) {
    const payload: TransactionCreate = {
      ...data,
      currency: cfg.currency,
      fx_rate: isUSD ? parseFloat(data.fx_rate_input) : undefined,
    }
    createTx(payload, { onSuccess: onClose })
  }

  // ─── Render ────────────────────────────────────────────────────────────────
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 p-1">

      {/* Compra / Venda toggle */}
      <div className="flex rounded-lg overflow-hidden border border-light-border dark:border-dark-border">
        {TX_TYPES.slice(0, 2).map(t => (
          <button
            key={t.value} type="button"
            onClick={() => setValue('transaction_type', t.value)}
            className={clsx(
              'flex-1 py-2 text-sm font-medium transition-colors flex items-center justify-center gap-1.5',
              txType === t.value
                ? t.value === 'COMPRA'
                  ? 'bg-positive/15 text-positive'
                  : 'bg-negative/15 text-negative'
                : 'text-muted hover:text-gray-700 dark:hover:text-gray-300'
            )}
          >
            {t.value === 'COMPRA' ? '🟢' : '🔴'} {t.label}
          </button>
        ))}
      </div>

      {/* Outros tipos (Bonificação, Desdobramento, Grupamento) */}
      <div className="flex gap-2 flex-wrap">
        {TX_TYPES.slice(2).map(t => (
          <button
            key={t.value} type="button"
            onClick={() => setValue('transaction_type', t.value)}
            className={clsx(
              'px-3 py-1 rounded text-xs font-medium border transition-colors',
              txType === t.value
                ? 'bg-brand-primary/15 text-brand-primary border-brand-primary/30'
                : 'border-light-border dark:border-dark-border text-muted hover:text-gray-700'
            )}
          >{t.label}</button>
        ))}
      </div>

      {/* Tipo de ativo */}
      <div>
        <label className="form-label">Tipo de ativo</label>
        <select className="input mt-1" {...register('asset_type')}>
          {Object.entries(ASSET_CONFIGS).map(([v, c]) => (
            <option key={v} value={v}>{c.label}</option>
          ))}
        </select>
      </div>

      {/* ── RENDA FIXA ─────────────────────────────────────────────────────── */}
      {isRendaFixa && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="form-label">Emissor</label>
              <input className="input mt-1" placeholder="Ex: Banco XP" {...register('issuer')} />
            </div>
            <div>
              <label className="form-label">Tipo de título</label>
              <select className="input mt-1" {...register('bond_type')}>
                {BOND_TYPES.map(b => <option key={b}>{b}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="form-label">Indexador</label>
              <select className="input mt-1" {...register('indexer')}>
                {INDEXERS.map(i => <option key={i}>{i}</option>)}
              </select>
            </div>
            <div>
              <label className="form-label">Taxa do CDI (%)</label>
              <input type="number" step="0.01" className="input mt-1" placeholder="100" {...register('cdi_rate', { valueAsNumber: true })} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="form-label">Forma <span className="text-muted">(Opcional)</span></label>
              <select className="input mt-1" {...register('bond_form')}>
                {BOND_FORMS.map(f => <option key={f}>{f}</option>)}
              </select>
            </div>
            <div>
              <label className="form-label">Valor (Opcional)</label>
              <input type="number" step="0.01" className="input mt-1" placeholder="0,00"
                {...register('price', { valueAsNumber: true })} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 items-center">
            <div>
              <label className="form-label">Data da transação</label>
              <input type="date" className="input mt-1" {...register('transaction_date')} />
            </div>
            <div>
              <label className="form-label">Data de vencimento</label>
              <input type="date" className="input mt-1" {...register('maturity_date')} />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <label className="form-label mb-0">Liquidez diária</label>
            <Controller
              control={control}
              name="daily_liquidity"
              render={({ field }) => (
                <button
                  type="button"
                  role="switch"
                  aria-checked={field.value}
                  onClick={() => field.onChange(!field.value)}
                  className={clsx(
                    'relative inline-flex h-5 w-9 rounded-full transition-colors',
                    field.value ? 'bg-positive' : 'bg-light-border dark:bg-dark-border'
                  )}
                >
                  <span className={clsx(
                    'inline-block h-4 w-4 rounded-full bg-white shadow transition-transform mt-0.5',
                    field.value ? 'translate-x-4' : 'translate-x-0.5'
                  )} />
                </button>
              )}
            />
          </div>
        </>
      )}

      {/* ── DEMAIS ATIVOS ───────────────────────────────────────────────────── */}
      {!isRendaFixa && (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="form-label">Ativo</label>
              <input
                className="input mt-1 uppercase placeholder:normal-case"
                placeholder="Selecionar"
                {...register('ticker', { required: 'Obrigatório' })}
                onChange={e => setValue('ticker', e.target.value.toUpperCase())}
              />
              {errors.ticker && <p className="form-error">{errors.ticker.message}</p>}
            </div>
            <div>
              <label className="form-label">Data da transação</label>
              <input type="date" className="input mt-1" {...register('transaction_date', { required: true })} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="form-label">Quantidade</label>
              <input
                type="number"
                step={cfg.qtyStep}
                min={cfg.qtyStep}
                className="input mt-1"
                {...register('quantity', { required: true, valueAsNumber: true })}
              />
              {errors.quantity && <p className="form-error">Obrigatório</p>}
            </div>
            <div>
              <label className="form-label">Preço em {isUSD ? 'US$' : 'R$'}</label>
              <input
                type="number"
                step={isUSD ? '0.00000001' : '0.01'}
                min="0"
                className="input mt-1"
                placeholder="0,00"
                {...register('price', { required: true, valueAsNumber: true })}
              />
              {errors.price && <p className="form-error">Obrigatório</p>}
            </div>
          </div>

          {/* Cotacao USD/BRL (somente USD) */}
          {isUSD && (
            <div className="rounded-lg border border-brand-primary/20 bg-brand-primary/5 p-3">
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-medium text-brand-primary">Cotação USD/BRL</label>
                {loadingFx && <RefreshCw size={12} className="animate-spin text-muted" />}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted">US$ 1,00 =</span>
                <input
                  type="number"
                  step="0.0001"
                  min="0.01"
                  className="input py-1 text-xs w-32"
                  {...register('fx_rate_input', { required: isUSD })}
                />
                <span className="text-xs text-muted">R$</span>
                {fxData?.rate && (
                  <button
                    type="button"
                    onClick={() => setValue('fx_rate_input', String(fxData.rate.toFixed(4)))}
                    className="text-xs text-brand-primary hover:underline ml-auto"
                  >
                    Usar cotação atual ({fxData.rate.toFixed(4)})
                  </button>
                )}
              </div>
              {price > 0 && fxRate > 0 && (
                <p className="text-xs text-muted mt-2">
                  {formatUSD(price)} × {fxRate.toFixed(4)} = <span className="font-medium text-gray-700 dark:text-gray-300">{formatBRL(priceBrl)}</span> por unidade
                </p>
              )}
            </div>
          )}

          <div>
            <label className="form-label">Outros custos (R$) <span className="text-muted">(Opcional)</span></label>
            <input type="number" step="0.01" min="0" className="input mt-1"
              placeholder="0,00"
              {...register('fees', { valueAsNumber: true })} />
          </div>
        </>
      )}

      {/* Total calculado */}
      <div className="rounded-lg bg-light-100 dark:bg-dark-700 px-4 py-3 flex items-center justify-between">
        <span className="text-xs font-medium text-muted">Valor total</span>
        <div className="text-right">
          <span className={clsx(
            'text-base font-bold tabular-nums block',
            txType === 'VENDA' ? 'text-positive' : 'text-gray-900 dark:text-gray-100'
          )}>
            {isUSD
              ? `${formatUSD(totalOrig)} = ${formatBRL(totalBrl)}`
              : formatBRL(totalBrl)}
          </span>
        </div>
      </div>

      {/* Botoes */}
      <div className="flex justify-between items-center pt-1">
        <button type="button" onClick={onClose} className="btn-secondary px-4 py-2 text-sm">
          Cancelar
        </button>
        <button
          type="submit"
          disabled={isPending}
          className={clsx(
            'px-5 py-2 text-sm font-medium rounded transition-colors flex items-center gap-2',
            txType === 'COMPRA' ? 'bg-positive text-white hover:bg-positive/90'
            : txType === 'VENDA' ? 'bg-negative text-white hover:bg-negative/90'
            : 'btn-primary'
          )}
        >
          {isPending ? 'Salvando…' : `+ Adicionar Lançamento`}
        </button>
      </div>
    </form>
  )
}
