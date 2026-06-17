import clsx from 'clsx'
import { formatPercent, signClass } from '@/utils/format'

interface Props {
  label: string
  value: string
  valueColor?: string
  change?: number
  subValue?: string
  subLabel?: string
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
    <div
      className="card flex flex-col gap-0.5"
      style={{ padding: '14px 16px 12px' }}
    >
      {/* Rótulo */}
      <span
        style={{
          fontSize: '0.7rem',
          fontWeight: 500,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: 'var(--color-text-faint)',
        }}
      >
        {label}
      </span>

      {/* Valor principal */}
      <div
        className={clsx('tabular-nums tracking-tight leading-none', valueColor ?? '')}
        style={{
          fontSize: '1.35rem',
          fontWeight: 700,
          marginTop: '4px',
          color: !valueColor ? 'var(--color-text)' : undefined,
        }}
      >
        {value}
      </div>

      {/* Variação % */}
      {change !== undefined && (
        <div
          className={clsx('tabular-nums', signClass(change))}
          style={{ fontSize: '0.72rem', fontWeight: 600, marginTop: '2px' }}
        >
          {change >= 0 ? '+' : ''}{formatPercent(change)}
        </div>
      )}

      {/* Segundo valor */}
      {subValue && (
        <div
          className="tabular-nums"
          style={{
            fontSize: '0.8rem',
            fontWeight: 500,
            marginTop: '4px',
            color: 'var(--color-text-muted)',
          }}
        >
          {subValue}
        </div>
      )}

      {/* Legenda auxiliar */}
      {subLabel && (
        <div
          className="truncate"
          style={{ fontSize: '0.68rem', color: 'var(--color-text-faint)', marginTop: '1px' }}
        >
          {subLabel}
        </div>
      )}

      {/* Rodapé extra */}
      {bottomLine && (
        <div
          style={{
            marginTop: '8px',
            paddingTop: '8px',
            borderTop: '1px solid oklch(from var(--color-text) l c h / 0.07)',
          }}
        >
          {bottomLine}
        </div>
      )}
    </div>
  )
}
