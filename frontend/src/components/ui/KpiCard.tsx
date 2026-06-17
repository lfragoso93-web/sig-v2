import clsx from 'clsx'
import { formatPercent, signClass } from '@/utils/format'

interface Props {
  label: string
  /** Valor principal — sempre exibido grande */
  value: string
  /** Cor opcional para o valor principal (ex: signClass) */
  valueColor?: string
  /** Variação percentual exibida logo abaixo do valor */
  change?: number
  /** Segunda linha em destaque (ex: valor investido) */
  subValue?: string
  /** Legenda / descrição auxiliar */
  subLabel?: string
  /** Linha extra no rodapé do card (ex: rentabilidade total) */
  bottomLine?: React.ReactNode
}

export default function KpiCard({
  label,
  value,
  valueColor,
  change,
  subValue,
  subLabel,
  bottomLine,
}: Props) {
  return (
    <div className="card p-4 flex flex-col gap-1 min-h-[96px]">
      {/* Rótulo */}
      <span
        className="text-xs font-medium uppercase tracking-wide"
        style={{ color: 'var(--color-text-muted)' }}
      >
        {label}
      </span>

      {/* Valor principal */}
      <div
        className={clsx(
          'text-xl font-bold tabular-nums tracking-tight leading-tight',
          valueColor ?? ''
        )}
        style={!valueColor ? { color: 'var(--color-text)' } : undefined}
      >
        {value}
      </div>

      {/* Variação % */}
      {change !== undefined && (
        <div className={clsx('text-xs font-semibold tabular-nums', signClass(change))}>
          {change >= 0 ? '+' : ''}{formatPercent(change)}
        </div>
      )}

      {/* Segundo valor */}
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
        <div
          className="text-xs truncate"
          style={{ color: 'var(--color-text-faint)' }}
        >
          {subLabel}
        </div>
      )}

      {/* Linha extra no rodapé (rentabilidade, etc.) */}
      {bottomLine && (
        <div className="mt-auto pt-2" style={{ borderTop: '1px solid var(--color-divider)' }}>
          {bottomLine}
        </div>
      )}
    </div>
  )
}
