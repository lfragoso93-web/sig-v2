import clsx from 'clsx'
import { signClass } from '@/utils/format'

interface Props {
  label: string
  value: string
  subValue?: string
  subLabel?: string
  change?: number
}

export default function KpiCard({ label, value, subValue, subLabel, change }: Props) {
  return (
    <div className="rounded-xl bg-surface-900 border border-surface-700 p-4 flex flex-col gap-1">
      <span className="text-xs text-slate-500 font-medium">{label}</span>
      <div className="text-2xl font-bold tabular-nums tracking-tight text-slate-100">{value}</div>
      {subValue && (
        <div className="text-sm font-medium text-slate-300 tabular-nums">{subValue}</div>
      )}
      {subLabel && (
        <div className="text-xs text-slate-500 truncate">{subLabel}</div>
      )}
      {change !== undefined && (
        <div className={clsx('text-xs font-semibold tabular-nums', signClass(change))}>
          {change >= 0 ? '+' : ''}{change.toFixed(2)}%
        </div>
      )}
    </div>
  )
}
