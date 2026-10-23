import React from 'react'
import clsx from 'clsx'
import {
  Wallet,
  TrendingUp,
  Coins,
  BarChart3,
  PiggyBank,
  CalendarClock,
  Activity,
  Award,
} from 'lucide-react'
import { formatPercent } from '@/utils/format'
import TwrHelpPopover from './TwrHelpPopover'

/** Converte qualquer valor para número seguro (0 se null/undefined/NaN/Infinity) */
function safeNum(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

function resolveDefaultKpiIcon(label: string): React.ElementType {
  const norm = label.toLowerCase()
  if (norm.includes('patrimônio') || norm.includes('patrimonio') || norm.includes('investido')) {
    return Wallet
  }
  if (norm.includes('provento') || norm.includes('recebido') || norm.includes('dividendo')) {
    return Coins
  }
  if (norm.includes('a receber') || norm.includes('média') || norm.includes('media')) {
    return CalendarClock
  }
  if (norm.includes('twr') || norm.includes('rentabilidade') || norm.includes('retorno')) {
    return Activity
  }
  if (norm.includes('realizado') && !norm.includes('não') && !norm.includes('nao')) {
    return Award
  }
  if (norm.includes('resultado') || norm.includes('lucro') || norm.includes('ganho')) {
    return TrendingUp
  }
  if (norm.includes('aporte') || norm.includes('custo')) {
    return PiggyBank
  }
  return BarChart3
}

export interface KpiCardProps {
  label: string
  value: React.ReactNode
  valueColor?: string
  change?: number | null
  subValue?: string
  subLabel?: string
  bottomLine?: React.ReactNode
  icon?: React.ElementType | null
  showTwrHelp?: boolean
}

export default function KpiCard({
  label,
  value,
  valueColor,
  change,
  subValue,
  subLabel,
  bottomLine,
  icon,
  showTwrHelp,
}: KpiCardProps) {
  // change pode chegar null/undefined da API — normaliza para número seguro
  const safeChange = change !== undefined && change !== null ? safeNum(change) : undefined
  const isPositive = safeChange !== undefined && safeChange >= 0
  const ResolvedIcon = icon === null ? null : (icon ?? resolveDefaultKpiIcon(label))
  const shouldShowTwrHelp = showTwrHelp ?? /\bTWR\b/i.test(label)

  return (
    <div
      className="card kpi-card-surface flex flex-col justify-between"
      style={{
        padding: '0.85rem 1rem',
        minHeight: '86px',
        gap: 0,
      }}
    >
      <div>
        {/* Cabeçalho: Rótulo + Ajuda TWR + Ícone canônico */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.45rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', minWidth: 0 }}>
            <span
              style={{
                fontSize: '0.6875rem',
                fontWeight: 600,
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                color: 'var(--color-text-muted)',
                lineHeight: 1.25,
              }}
            >
              {label}
            </span>
            {shouldShowTwrHelp && <TwrHelpPopover />}
          </div>

          {ResolvedIcon && (
            <span
              aria-hidden="true"
              style={{
                width: 24,
                height: 24,
                borderRadius: 'var(--radius-sm)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
                background: 'oklch(from var(--color-primary) l c h / 0.09)',
                color: 'var(--color-primary)',
                border: '1px solid oklch(from var(--color-primary) l c h / 0.14)',
              }}
            >
              <ResolvedIcon size={13} strokeWidth={2} />
            </span>
          )}
        </div>

        {/* Valor principal + badge de variação */}
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '0.4rem',
            marginTop: '0.45rem',
          }}
        >
          <div
            className={clsx('tabular-nums tracking-tight', valueColor ?? '')}
            style={{
              fontSize: 'clamp(1rem, 0.88rem + 0.45vw, 1.2rem)',
              fontWeight: 700,
              lineHeight: 1.15,
              color: !valueColor ? 'var(--color-text)' : undefined,
              letterSpacing: '-0.02em',
            }}
          >
            {value}
          </div>

          {/* Variação % */}
          {safeChange !== undefined && (
            <div
              className="tabular-nums"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: '0.12em 0.5em',
                borderRadius: 'var(--radius-full)',
                fontSize: '0.6875rem',
                fontWeight: 600,
                lineHeight: 1.35,
                background: isPositive
                  ? 'oklch(from var(--color-success) l c h / 0.12)'
                  : 'oklch(from var(--color-notification) l c h / 0.12)',
                color: isPositive ? 'var(--color-success)' : 'var(--color-notification)',
              }}
            >
              {safeChange >= 0 ? '+' : ''}
              {formatPercent(safeChange)}
            </div>
          )}
        </div>
      </div>

      {/* Sub-info e rodapé */}
      {(subValue || subLabel || bottomLine) && (
        <div style={{ marginTop: '0.5rem' }}>
          {(subValue || subLabel) && (
            <div
              style={{
                paddingTop: '0.45rem',
                borderTop: '1px solid oklch(from var(--color-text) l c h / 0.065)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.1rem',
              }}
            >
              {subValue && (
                <div
                  className="tabular-nums"
                  style={{
                    fontSize: 'var(--text-xs)',
                    fontWeight: 600,
                    color: 'var(--color-text-muted)',
                    lineHeight: 1.2,
                  }}
                >
                  {subValue}
                </div>
              )}

              {subLabel && (
                <div
                  style={{
                    fontSize: '0.6875rem',
                    color: 'var(--color-text-faint)',
                    lineHeight: 1.3,
                    wordBreak: 'break-word',
                  }}
                >
                  {subLabel}
                </div>
              )}
            </div>
          )}

          {bottomLine && (
            <div
              style={{
                marginTop: subValue || subLabel ? '0.4rem' : 0,
                paddingTop: '0.4rem',
                borderTop: '1px solid oklch(from var(--color-text) l c h / 0.065)',
              }}
            >
              {bottomLine}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
