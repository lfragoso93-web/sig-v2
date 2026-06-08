import { ReactNode } from 'react'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'

interface KpiCardProps {
  label: string
  value: string
  subValue?: string
  subLabel?: string
  change?: number
  children?: ReactNode
  className?: string
}

export default function KpiCard({ label, value, subValue, subLabel, change, children, className }: KpiCardProps) {
  const isPositive = change !== undefined && change > 0
  const isNegative = change !== undefined && change < 0

  return (
    <div className={clsx('card p-4 flex flex-col gap-1', className)}>
      <span className="text-xs text-muted font-medium">{label}</span>
      <span className="text-2xl font-bold tabular-nums tracking-tight text-gray-900 dark:text-gray-100">
        {value}
      </span>
      {(subValue || subLabel) && (
        <span className="text-xs text-muted">
          {subValue && <span className="text-gray-700 dark:text-gray-300">{subValue}</span>}
          {subLabel && <span> {subLabel}</span>}
        </span>
      )}
      {change !== undefined && (
        <div className={clsx('flex items-center gap-1 text-sm font-medium mt-0.5',
          isPositive ? 'text-positive' : isNegative ? 'text-negative' : 'text-muted'
        )}>
          {isPositive ? <TrendingUp size={14} /> : isNegative ? <TrendingDown size={14} /> : <Minus size={14} />}
          <span>{change > 0 ? '+' : ''}{change.toFixed(2)}%</span>
        </div>
      )}
      {children}
    </div>
  )
}
