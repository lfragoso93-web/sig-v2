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
      className="card flex flex-col"
      style={{ padding: '14px 16px', minHeight: '96px', gap: '2px' }}
    >
      {/* Rótulo */}
      <span
        style={{
          fontSize: '0.68rem',
          fontWeight: 500,
          letterSpacing: '0.07em',
          textTransform: 'uppercase',
          color: 'var(--color-text-faint)',
          lineHeight: 1,
        }}
      >
        {label}
      </span>

      {/* Valor principal */}
      <div
        className={clsx('tabular-nums tracking-tight leading-tight', valueColor ?? '')}
        style={{
          fontSize: '1.05rem',
          fontWeight: 700,
          marginTop: '6px',
          color: !valueColor ? 'var(--color-text)' : undefined,
        }}
      >
        {value}
      </div>

      {/* Variação % */}
      {change !== undefined && (
        <div
          className={clsx('tabular-nums', signClass(change))}
          style={{ fontSize: '0.7rem', fontWeight: 600, marginTop: '2px', lineHeight: 1 }}
        >
          {change >= 0 ? '+' : ''}{formatPercent(change)}
        </div>
      )}

      {/* Segundo valor */}
      {subValue && (
        <div
          className="tabular-nums"
          style={{
            fontSize: '0.78rem',
            fontWeight: 500,
            marginTop: '5px',
            color: 'var(--color-text-muted)',
            lineHeight: 1,
          }}
        >
          {subValue}
        </div>
      )}

      {/* Legenda auxiliar */}
      {subLabel && (
        <div
          className="truncate"
          style={{ fontSize: '0.67rem', color: 'var(--color-text-faint)', marginTop: '2px', lineHeight: 1.2 }}
        >
          {subLabel}
        </div>
      )}

      {/* Rodapé extra */}
      {bottomLine && (
        <div
          style={{
            marginTop: 'auto',
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
