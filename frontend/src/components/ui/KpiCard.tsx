import clsx from 'clsx'
import { formatPercent, signClass } from '@/utils/format'

interface Props {
  label: string
  /** Valor principal — sempre exibido grande (ex: formatBRL) */
  value: string
  /** Variação percentual (ex: -1.81) — exibida logo abaixo do valor principal */
  change?: number
  /** Segunda linha de valor em destaque (ex: valor investido) */
  subValue?: string
  /** Legenda / descrição do subValue ou texto auxiliar */
  subLabel?: string
}

export default function KpiCard({ label, value, change, subValue, subLabel }: Props) {
  return (
    <div className="card p-4 flex flex-col gap-1">
      {/* Rótulo */}
      <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
        {label}
      </span>

      {/* Valor principal (R$) */}
      <div
        className="text-2xl font-bold tabular-nums tracking-tight"
        style={{ color: 'var(--color-text)' }}
      >
        {value}
      </div>

      {/* Variação % — imediatamente abaixo do valor */}
      {change !== undefined && (
        <div className={clsx('text-xs font-semibold tabular-nums', signClass(change))}>
          {change >= 0 ? '+' : ''}{formatPercent(change)}
        </div>
      )}

      {/* Segundo valor em destaque (ex: total investido) */}
      {subValue && (
        <div
          className="text-sm font-medium tabular-nums mt-0.5"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {subValue}
        </div>
      )}

      {/* Legenda auxiliar */}
      {subLabel && (
        <div className="text-xs truncate" style={{ color: 'var(--color-text-faint)' }}>
          {subLabel}
        </div>
      )}
    </div>
  )
}
