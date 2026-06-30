import React from 'react'
import clsx from 'clsx'
import { formatPercent } from '@/utils/format'

/** Converte qualquer valor para número seguro (0 se null/undefined/NaN/Infinity) */
function safeNum(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

interface Props {
  label: string
  value: React.ReactNode
  valueColor?: string
  change?: number | null
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
  // change pode chegar null/undefined da API — normaliza para número seguro
  const safeChange = change !== undefined && change !== null ? safeNum(change) : undefined
  const isPositive = safeChange !== undefined && safeChange >= 0

  return (
    <div
      className="card flex flex-col"
      style={{
        padding:   'clamp(0.875rem, 1.1vw, 1.125rem) clamp(1rem, 1.3vw, 1.25rem)',
        minHeight: 'clamp(88px, 7.5vw, 108px)',
        gap:       0,
      }}
    >
      {/* Rótulo */}
      <span
        style={{
          fontSize:      'var(--text-xs)',
          fontWeight:    500,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color:         'var(--color-text-faint)',
          lineHeight:    1,
        }}
      >
        {label}
      </span>

      {/* Valor principal */}
      <div
        className={clsx('tabular-nums tracking-tight', valueColor ?? '')}
        style={{
          fontSize:      'clamp(1rem, 0.82rem + 0.8vw, 1.3rem)',
          fontWeight:    660,
          lineHeight:    1.15,
          marginTop:     10,
          color:         !valueColor ? 'var(--color-text)' : undefined,
          letterSpacing: '-0.015em',
        }}
      >
        {value}
      </div>

      {/* Variação % */}
      {safeChange !== undefined && (
        <div
          className="tabular-nums"
          style={{
            display:      'inline-flex',
            alignItems:   'center',
            alignSelf:    'flex-start',
            marginTop:    6,
            padding:      '0.15em 0.45em',
            borderRadius: 'var(--radius-full)',
            fontSize:     'var(--text-xs)',
            fontWeight:   600,
            lineHeight:   1.5,
            background:   isPositive
              ? 'oklch(from var(--color-success) l c h / 0.12)'
              : 'oklch(from var(--color-notification) l c h / 0.12)',
            color: isPositive ? 'var(--color-success)' : 'var(--color-notification)',
          }}
        >
          {safeChange >= 0 ? '+' : ''}{formatPercent(safeChange)}
        </div>
      )}

      {/* Divisor visual antes da sub-info */}
      {(subValue || subLabel) && (
        <div
          style={{
            height:     '1px',
            background: 'oklch(from var(--color-text) l c h / 0.07)',
            marginTop:  10,
            marginBottom: 8,
          }}
        />
      )}

      {/* Segundo valor */}
      {subValue && (
        <div
          className="tabular-nums"
          style={{
            fontSize:   'var(--text-sm)',
            fontWeight: 500,
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
            fontSize:   'var(--text-xs)',
            color:      'var(--color-text-faint)',
            marginTop:  subValue ? 3 : 0,
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
            paddingTop: 8,
            borderTop:  '1px solid oklch(from var(--color-text) l c h / 0.07)',
          }}
        >
          {bottomLine}
        </div>
      )}
    </div>
  )
}
