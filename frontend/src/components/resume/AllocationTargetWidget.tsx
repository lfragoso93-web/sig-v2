import { useState } from 'react'
import { Target } from 'lucide-react'
import type { ClassTargetRow } from '@/hooks/useClassTargets'

/** Conversão segura para número — evita toFixed em null/undefined/NaN */
function safe(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

/**
 * AllocationTargetWidget
 * ---------------------------------------------------------------------------
 * Exibe barras de progresso para cada classe de ativo configurada em Metas,
 * comparando o percentual atual com o alvo configurado pelo usuário.
 *
 * Pode ser usado tanto na ResumePage (card lateral de Distribuição)
 * quanto na PatrimonioPage (aba Visão Geral).
 * ---------------------------------------------------------------------------
 */
export interface AllocationTargetWidgetProps {
  rows: ClassTargetRow[]
  /** Remove o margin-top padrão (útil quando o pai já tem padding) */
  noTopMargin?: boolean
}

export default function AllocationTargetWidget({ rows, noTopMargin = false }: AllocationTargetWidgetProps) {
  const [collapsed, setCollapsed] = useState(false)

  const hasAnyTarget = rows.some(r => safe(r.target_pct) > 0)
  if (!hasAnyTarget) {
    return (
      <div style={{
        marginTop: noTopMargin ? 0 : '0.75rem',
        padding: '10px 12px',
        borderRadius: 'var(--radius-md)',
        background: 'var(--color-surface-offset)',
        border: '1px dashed oklch(from var(--color-text) l c h / 0.1)',
        textAlign: 'center',
      }}>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>
          Configure metas em{' '}
          <a href="/carteira/metas" style={{ color: 'var(--color-primary)', textDecoration: 'underline' }}>
            Configurações → Metas
          </a>
        </span>
      </div>
    )
  }

  return (
    <div style={{ marginTop: noTopMargin ? 0 : '0.75rem' }}>
      {/* Header colapsável */}
      <button
        onClick={() => setCollapsed(c => !c)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          width: '100%', background: 'none', border: 'none',
          cursor: 'pointer', padding: '2px 0', marginBottom: collapsed ? 0 : '0.5rem',
        }}
      >
        <Target size={12} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)' }}>
          Alvo da Carteira
        </span>
        <span style={{
          marginLeft: 'auto',
          fontSize: '0.6rem',
          color: 'var(--color-text-faint)',
          transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
          transition: 'transform 0.15s',
        }}>▼</span>
      </button>

      {!collapsed && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
          {rows.map(row => {
            const currentPct = safe(row.current_pct)
            const targetPct  = safe(row.target_pct)
            const delta      = safe(row.delta_pct)

            const statusColor =
              Math.abs(delta) <= 2
                ? 'var(--color-success)'
                : delta > 0
                  ? 'var(--color-error)'
                  : 'var(--color-warning)'

            const barMax   = Math.max(currentPct, targetPct, 1)
            const currentW = Math.min((currentPct / barMax) * 100, 100)
            const targetW  = Math.min((targetPct  / barMax) * 100, 100)

            return (
              <div key={row.asset_type}>
                {/* Label + delta */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 3 }}>
                  <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)', fontWeight: 500 }}>
                    {row.label}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: '0.68rem', color: 'var(--color-text-faint)' }}>
                      {currentPct.toFixed(1)}%{' '}
                      <span style={{ color: 'var(--color-text-faint)', fontWeight: 400 }}>
                        / alvo {targetPct.toFixed(1)}%
                      </span>
                    </span>
                    {targetPct > 0 && (
                      <span style={{
                        fontSize: '0.62rem', fontWeight: 700,
                        color: statusColor,
                        minWidth: 36, textAlign: 'right',
                      }}>
                        {delta > 0 ? '+' : ''}{delta.toFixed(1)}pp
                      </span>
                    )}
                  </div>
                </div>

                {/* Barra de progresso */}
                <div style={{
                  position: 'relative',
                  height: 6,
                  borderRadius: 'var(--radius-full)',
                  background: 'var(--color-surface-offset)',
                  overflow: 'visible',
                }}>
                  {/* Barra atual */}
                  <div style={{
                    position: 'absolute', top: 0, left: 0,
                    height: '100%',
                    width: `${currentW}%`,
                    background: row.color,
                    borderRadius: 'var(--radius-full)',
                    opacity: 0.85,
                    transition: 'width 0.4s ease',
                  }} />
                  {/* Marcador de alvo (linha vertical) */}
                  {targetPct > 0 && (
                    <div style={{
                      position: 'absolute',
                      top: -3, bottom: -3,
                      left: `${targetW}%`,
                      width: 2,
                      background: 'var(--color-text-muted)',
                      borderRadius: 1,
                      opacity: 0.55,
                      transform: 'translateX(-50%)',
                    }} />
                  )}
                </div>
              </div>
            )
          })}

          {/* Legenda compacta */}
          <div style={{ display: 'flex', gap: 10, marginTop: 4, flexWrap: 'wrap' }}>
            {[
              { color: 'var(--color-success)', label: '±2pp do alvo' },
              { color: 'var(--color-warning)', label: 'Subalocado'   },
              { color: 'var(--color-error)',   label: 'Sobrealocado' },
            ].map(leg => (
              <div key={leg.label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: leg.color, flexShrink: 0 }} />
                <span style={{ fontSize: '0.6rem', color: 'var(--color-text-faint)' }}>{leg.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
