import clsx from 'clsx'
import { formatPercent, signClass } from '@/utils/format'

interface Props {
  label: string
  value: string
  subValue?: string
  subLabel?: string
  change?: number   // valor em percentual, ex: -1.81 ou 4.52
}

export default function KpiCard({ label, value, subValue, subLabel, change }: Props) {
  return (
    <div className="card p-4 flex flex-col gap-1">
      <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
        {label}
      </span>
      <div
        className="text-2xl font-bold tabular-nums tracking-tight"
        style={{ color: 'var(--color-text)' }}
      >
        {value}
      </div>
      {subValue && (
        <div
          className="text-sm font-medium tabular-nums"
          style={{ color: 'var(--color-text-muted)' }}
        >
          {subValue}
        </div>
      )}
      {subLabel && (
        <div className="text-xs truncate" style={{ color: 'var(--color-text-faint)' }}>
          {subLabel}
        </div>
      )}
      {change !== undefined && (
        <div className={clsx('text-xs font-semibold tabular-nums', signClass(change))}>
          {change >= 0 ? '+' : ''}{formatPercent(change)}
        </div>
      )}
    </div>
  )
}
