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
  const isPositive = change !== undefined && change >= 0

  return (
    <div
      className="card flex flex-col"
      style={{
        /* Padding fluido: 16px mobile → 20px desktop */
        padding:   'clamp(1rem, 1.25vw, 1.25rem) clamp(1rem, 1.5vw, 1.375rem)',
        minHeight: 'clamp(96px, 8vw, 112px)',
        gap:       '3px',
      }}
    >
      {/* Rótulo */}
      <span
        style={{
          fontSize:      'var(--text-xs)',
          fontWeight:    500,
          letterSpacing: '0.07em',
          textTransform: 'uppercase',
          color:         'var(--color-text-faint)',
          lineHeight:    1,
        }}
      >
        {label}
      </span>

      {/* Valor principal — fluido entre 17px e 22px */}
      <div
        className={clsx('tabular-nums tracking-tight', valueColor ?? '')}
        style={{
          fontSize:   'clamp(1.0625rem, 0.88rem + 0.85vw, 1.375rem)',
          fontWeight: 660,
          lineHeight: 1.15,
          marginTop:  'var(--space-2)',
          color:      !valueColor ? 'var(--color-text)' : undefined,
          letterSpacing: '-0.01em',
        }}
      >
        {value}
      </div>

      {/* Variação % — como badge pill */}
      {change !== undefined && (
        <div
          className="tabular-nums"
          style={{
            display:        'inline-flex',
            alignItems:     'center',
            alignSelf:      'flex-start',
            marginTop:      'var(--space-1)',
            padding:        '0.15em 0.5em',
            borderRadius:   'var(--radius-full)',
            fontSize:       'var(--text-xs)',
            fontWeight:     600,
            lineHeight:     1.5,
            background:     isPositive
              ? 'oklch(from var(--color-success) l c h / 0.12)'
              : 'oklch(from var(--color-notification) l c h / 0.12)',
            color: isPositive ? 'var(--color-success)' : 'var(--color-notification)',
          }}
        >
          {change >= 0 ? '+' : ''}{formatPercent(change)}
        </div>
      )}

      {/* Segundo valor */}
      {subValue && (
        <div
          className="tabular-nums"
          style={{
            fontSize:  'var(--text-sm)',
            fontWeight: 500,
            marginTop:  'var(--space-2)',
            color:      'var(--color-text-muted)',
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
          style={{
            fontSize:  'var(--text-xs)',
            color:     'var(--color-text-faint)',
            marginTop: 'var(--space-0-5)',
            lineHeight: 1.3,
          }}
        >
          {subLabel}
        </div>
      )}

      {/* Rodapé extra */}
      {bottomLine && (
        <div
          style={{
            marginTop:  'auto',
            paddingTop: 'var(--space-3)',
            borderTop:  '1px solid oklch(from var(--color-text) l c h / 0.07)',
          }}
        >
          {bottomLine}
        </div>
      )}
    </div>
  )
}
